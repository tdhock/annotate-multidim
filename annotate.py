#!/usr/bin/python

from Tkinter import *
import os,csv,gzip,glob,pdb

## This defines the expected column names in the annotation data file.
ANN_COLUMNS = ["class","instance","dim","min","max","annotation"]
ANN_HEADER = ",".join(ANN_COLUMNS)


## This defines the color to use for plotting points, and also for
## annotations which are found in the database, but not in the list of
## annotations below.
POINT_COLOR = "blue"

## this defines the colors to display for the annotations and the
## order in which to display them.
ANNOTATION_ORDER=[
        ("onset","#ff7d7d"),
        ("nothing",'#f6f4bf'),
        ]
ANNOTATIONS=[a for a,c in ANNOTATION_ORDER]
NEXT_ANNOTATION=dict(zip(ANNOTATIONS,ANNOTATIONS[1:]))
REGION_COLORS=dict(ANNOTATION_ORDER)

def get_converter(L):
    """Figure out the types for reading csv data."""
    try:
        tmp = [int(x) for x in L]
        return int
    except ValueError:
        return str

class Region(dict):
    def __init__(self,annotation,first,last,dim):
        self.update({
                "annotation":annotation,
                "min":first,
                "max":last,
                "dim":dim,
                })
    def onClick(self,e):
        ## cycle through annotations as specified in ANNOTATION_ORDER
        if self["annotation"] in NEXT_ANNOTATION:
            self["annotation"]=NEXT_ANNOTATION[self["annotation"]]
            fill=REGION_COLORS[self["annotation"]]
            e.widget.itemconfig(self.id,fill=fill,outline=fill)
        else:
            e.widget.delete(self.id)
            self.regions.pop(self.region_index)
        return "break"

class SeriesDB(dict):
    def __init__(self, db):
        class_dirs = os.listdir(db)
        for class_dir in class_dirs:
            class_path = os.path.join(db,class_dir)
            instance_files = os.listdir(class_path)
            for f in instance_files:
                inst_id = os.path.basename(f).replace(".csv.gz","")
                self[(class_dir,inst_id)] = {
                    "file":os.path.join(class_path,f),
                    "class":class_dir,
                    "instance":inst_id,
                    }
    def get(self, k):
        d = self[k]
        if "data" not in d:
            f = gzip.open(d["file"])
            reader = csv.reader(f, lineterminator="\n", delimiter=",")
            tup_list = [
                [float(x) for x in tup] for tup in reader
                ]
            #print "Read %10d lines from %s"%(len(tup_list), d["file"])
            d["data"] = zip(*tup_list)
        return d["data"]

class RegionDB(dict):
    """Container for all the annotations in a database.

    """
    def __init__(self,regions_file):
        ## if file does not exist, will create when we exit
        self.regions_file = regions_file
        self.regions_read = 0
        try:
            f=open(regions_file)
            reader=csv.reader(f,lineterminator="\n",delimiter=",")
            header_items = reader.next()
            stripped = [i.strip() for i in header_items]
            header = ",".join(stripped)
            if header != ANN_HEADER:
                raise ValueError("first line of %s was '%s' expected '%s'"%(
                        regions_file,header,ANN_HEADER))
            for klass,inst,dim,first,last,annotation in reader:
                self.regions_read +=1
                r = Region(annotation,int(first),int(last),int(dim)-1)
                k = (klass,inst)
                self.add(k,r)
            f.close()
        except StopIteration:
            print "No annotations detected, will overwrite %s"%regions_file
        except IOError:
            print "%s does not exist, will write on exit"%regions_file
    def count(self,tup):
        if tup in self:
            return len(self[tup])
        return 0
    def add(self,k,region):
        if k not in self:
            self[k] = RegionList()
        self[k].add(region)
    def get(self,k):
        if k not in self:
            self[k] = RegionList()
        return self[k]
    def save(self):
        lines = [ANN_HEADER]
        for (klass,inst),region_list in self.iteritems():
            for r in region_list.values():
                r["class"]=klass
                r["instance"]=inst
                r["dim"] += 1
                items = [str(r[k]) for k in ANN_COLUMNS]
                lines.append(",".join(items))
        text = "\n".join(lines)+"\n"
        f=open(self.regions_file,"w")
        f.write(text)
        f.close()
        print "Saved %d annotations to %s"%(len(lines)-1,self.regions_file)

class RegionList(dict):
    """container for annotated regions for 1 series.

    facilitates deletion more automatically by passing the keys and
    the container reference to the items themselves, so they can
    remove themselves."""
    def __init__(self):
        self.counter = 0
    def add(self,r):
        r.regions = self
        self[self.counter] = r
        r.region_index = self.counter
        self.counter += 1

class AnnotatedPlot(Canvas):
    """Canvas with special onclick"""
    def onClick(self,e):
        self.orig_x = self.canvasx(e.x)
        self.resize_rect(e)
    def onMotion(self,e):
        self.delete(self.new_id)
        self.resize_rect(e)
    def resize_rect(self,e):
        x = self.canvasx(e.x)
        if x < 0:
            x=0
        if x > self.w:
            x=self.w
        if self.orig_x < x:
            self.left = self.orig_x
            self.right = x
        else:
            self.left = x
            self.right = self.orig_x
        self.new_id = self.make_rect(
            self.left,self.right,ANNOTATION_ORDER[0][1])
    def make_rect(self,left,right,fill):
        id = self.create_rectangle(
            left,1,right,self.h,fill=fill,outline=fill,activeoutline="black",
            tag="region")
        self.tag_lower("lines")
        self.tag_lower("region")
        self.tag_lower(self.bgid)
        self.tag_lower("interval")
        return id
    def to_position(self,pixels):
        return int(pixels * self.l / self.w + self.m)
    def to_pixels(self,position):
        #print position,self.m,self.w,self.l
        return int(float(position-self.m)*self.w/self.l)
    def onRelease(self,e):
        r = Region(
            ANNOTATION_ORDER[0][0],
            self.to_position(self.left),
            self.to_position(self.right),
            self.dim,
            )
        r.id = self.new_id
        self.tag_bind(self.new_id,"<Button-1>",r.onClick)
        self.regions.add(r)
        #print self.regions

class Annotator(object):
    def onClose(self):
        """Save annotations to file before quitting."""
        self.region_db.save()
        self.root.destroy()
    def __init__(self,root,db,ann_file,starting_klass=None):
        self.root = root
        root.protocol("WM_DELETE_WINDOW",self.onClose)
        ## save file names for later to save annotations
        self.series_db = SeriesDB(db)
        self.region_db = RegionDB(ann_file)
        print "Database contains %d series and %d annotations."%(
            len(self.series_db), self.region_db.regions_read)
        # Make a list of series ids that we can use as the display order.
        self.series_ids = self.series_db.keys()
        kconv = get_converter([klass for klass,inst in self.series_ids])
        iconv = get_converter([inst for klass,inst in self.series_ids])
        self.series_ids.sort(key=lambda x: (kconv(x[0]), iconv(x[1])))
        # fix it as mutable forevermore.
        self.series_ids = tuple(self.series_ids)
        self.series_class = tuple([kl for kl,i in self.series_ids])
        # make a list of series ordered by number of annotations.
        by_ann_counts = list(self.series_ids)
        by_ann_counts.sort(key=lambda x: self.region_db.count(x))
        if starting_klass is None:
            target_id = by_ann_counts[0]
        else:
            klass_list = [klass for klass,inst in by_ann_counts]
            kl_index = klass_list.index(starting_klass)
            target_id = by_ann_counts[kl_index]
        starting_index = self.series_ids.index(target_id)
        #print self.profiles.items()[:5]
        #print self.regions_dict.items()[:5]
        k = self.series_db.keys()[0]
        columns = self.series_db.get(k)
        print "%d-dimensional time series (matrix columns = rows to plot)."%(
            len(columns))
        INITIAL_WIDTH=root.winfo_screenwidth()-100
        INITIAL_HEIGHT=root.winfo_screenheight() -100
        ROWS = len(columns)
        PLOT_HEIGHT = self.get_plot_height(INITIAL_HEIGHT,ROWS)
        root.geometry("%sx%s+0+0"%(INITIAL_WIDTH,INITIAL_HEIGHT))
        #print INITIAL_WIDTH, PLOT_HEIGHT

        self.canvases = {}
        # there is one column of plots.
        for i,c in enumerate(columns):
            widget = AnnotatedPlot(root,background="white",
                                   width=INITIAL_WIDTH,
                                   height=PLOT_HEIGHT,borderwidth=0,
                                   highlightthickness=1,
                                   highlightbackground="grey",
                                   highlightcolor="red",
                                   )
            ## all this stuff doesnt change with profiles
            widget.dim = i
            widget.m = 1
            #widget.M = self.profiles.positionmax[j]
            #widget.l = self.profiles.chrom_lengths[j]
            widget.w = INITIAL_WIDTH
            widget.h = PLOT_HEIGHT
            #print widget.m,widget.M,widget.l,widget.w,widget.h
            widget.annotator = self ## for right-click callbacks
            widget.row = i
            self.canvases[i] = widget
            widget.grid(row=i,column=0,padx=0,pady=0)
        self.new_series(starting_index,resize=False)
    def get_plot_height(self,h,rows):
        return h / rows - 2
    def prevClass(self,e):
        current_class = self.series_class[self.active_index]
        class_first_index = self.series_class.index(current_class)
        prev_class_last_index = self.navigate(class_first_index-1)
        self.new_series(prev_class_last_index)
    def nextClass(self,e):
        current_class = self.series_class[self.active_index]
        dist_from_back = self.series_class[::-1].index(current_class)
        next_class_first_index = self.navigate(
            len(self.series_class)-dist_from_back)
        self.new_series(next_class_first_index)
    def navigate(self,i):
        if i >= len(self.series_ids):
            i = 0
        if i < 0:
            i = len(self.series_ids)-1
        return i
    def previous(self,e):
        self.move(-1)
    def next(self,e):
        self.move(1)
    def move(self,i):
        self.new_series(self.navigate(self.active_index+i))
    def new_series(self,index,resize=True):
        """Bind a time series to the display for annotation."""
        self.active_index = index
        self.active_id = self.series_ids[index]
        self.active_series = self.series_db.get(self.active_id)
        self.active_regions = self.region_db.get(self.active_id)
        series_length = len(self.active_series[0])
        tmp = " ".join([
                "class %2s instance %4s",
                "%10d x %2d matrix",
                "with %3d annotated regions",
                ])
        print tmp%(
            self.active_id[0], self.active_id[1], series_length,
            len(self.active_series), len(self.active_regions))
        # Figure out how big the window currently is in order to
        # adapt the width and height of the plot accordingly.
        if resize:
            CURRENT_WIDTH = root.winfo_width()
            CURRENT_HEIGHT = root.winfo_height()
            PLOT_HEIGHT = self.get_plot_height(
                CURRENT_HEIGHT,len(self.active_series))
        for i,col in enumerate(self.active_series):
            # calibrate new plot window with annotation positions.
            w=self.canvases[i]
            w.M = w.l = series_length
            # Right mouse clicks:
            #w.bind("<Button-3>",w.doneAnnotating)

            # Arrow keys:
            w.delete(ALL) ## delete previous contents first
            # guide lines if you want to see the 0 point for example.
            # LINES=[0,-1,1]
            # LINES_PX = [
            #     w.h * (1 -(x-p.logratiomin)/p.logratio_range)
            #     for x in LINES
            #     ]
            # y=LINES_PX[0]
            # w.create_rectangle(0,LINES_PX[1],w.w+1,LINES_PX[2],
            #                    fill="#e5e5e5",outline="",
            #                    tag="interval")

            # adapt the plot size based on the window size.
            if resize:
                w.config(width=CURRENT_WIDTH)
                w.config(height=PLOT_HEIGHT)
                w.w = CURRENT_WIDTH
                w.h = PLOT_HEIGHT

            w.bgid = w.create_rectangle(0,0,w.w,w.h,outline="",fill="")
            #w.create_line(0,y,w.w,y,tag="lines")
            w.tag_bind(w.bgid,"<Button-1>",w.onClick)
            w.tag_bind(w.bgid,"<B1-Motion>",w.onMotion)
            w.tag_bind(w.bgid,"<ButtonRelease-1>",w.onRelease)
            w.regions = self.active_regions
            for r in w.regions.values():
                if r["dim"] == i:
                    first = w.to_pixels(r["min"])
                    last = w.to_pixels(r["max"])
                    fill = REGION_COLORS.get(r["annotation"],POINT_COLOR)
                    r.id = w.make_rect(first,last,fill)
                    w.tag_bind(r.id,"<Button-1>",r.onClick)
            y_min = min(col)
            y_max = max(col)
            y_range = y_max - y_min
            if y_range == 0:
                y_max = col[0] + 1
                y_min = col[0] - 1
                y_range = y_max - y_min
            norm = [
                (y_i - y_min)/y_range
                for y_i in col
                ]
            y_px = [
                w.h - n*w.h
                for n in norm
                ]
            x_px = [
                (i-float(w.m))*w.w/w.l
                for i, y_i in enumerate(y_px)
                ]
            for x,y in zip(x_px,y_px):
                w.create_oval(x-1,y-1,x+1,y+1,fill="",outline=POINT_COLOR)

if __name__ == "__main__":
    import sys
    #root.state("zoomed") # to start maximized
    args=sys.argv[1:]
    if len(args) < 2:
        print """Usage: %s db annotations.csv
Inside db is a folder for every class, inside are matrix files.
annotations.csv has columns %s
"""%(sys.argv[0],ANN_HEADER)
        sys.exit(1)
    root = Tk()
    ann = Annotator(root,*args)
    root.bind("<Left>",ann.previous)
    root.bind("<Right>",ann.next)
    root.bind("<Down>",ann.prevClass)
    root.bind("<Up>",ann.nextClass)
    root.focus_set()
    root.mainloop()
