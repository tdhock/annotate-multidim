annotate-multidim
=================

Toby Dylan Hocking 25 July 2013

annotate.py for multidimensional time series.

Usage: python annotate.py db annotations.csv [class]

where db is a directory that contains a database of multidimensional
time series. For an example of how to make one of these databases, see
export.R. There is a db/class folder for each class, and a
db/class/instance.csv.gz file for each instance of that class, which
is a n x p matrix. The number of observations n is the length of the
time series which varies in each file, but the number of dimensions p
which is the number of distinct time series remains constant and is
read on program startup. We also read annotations.csv on startup,
which is a table that records the visual annotations.

Drag on the white background to create a new annotation. Click an
existing annotation to change its meaning, or delete it. The list of
annotations and colors is defined in the ANNOTATION_ORDER variable.

The optional class argument can be given on the command line to start
annotation with a given class ID. After that the left and right arrow
keys navigate between series, and the up and down arrows navigate
between classes.

The plot size can be changed by resizing the window, and then
navigating to another series using an arrow key.
