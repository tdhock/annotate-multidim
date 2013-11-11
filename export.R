price <- read.table("NYSEprice.txt",header=TRUE)

set.seed(1)
distributions <- list(rnorm,rexp)
dir.create("db", showWarnings=FALSE)
for(i in seq_along(distributions)){
  class.dir <- file.path("db",i)
  dir.create(class.dir, showWarnings=FALSE)
  rand <- distributions[[i]]
  for(j in 1:10){
    y <- price$Price
    x <- rand(length(y))
    m <- cbind(x,y)
    fn <- file.path(class.dir, sprintf("%d.csv.gz",j))
    conn <- gzfile(fn,"w")
    write.table(m,conn,sep=",",
                quote=FALSE,row.names=FALSE,col.names=FALSE)
    close(conn)
  }
}
