rm(list = ls())

### Check package availability ###

list.of.packages <- c("ggvenn")
new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
if(length(new.packages)) install.packages(new.packages)

### Load packages ###

suppressMessages(suppressWarnings(library("ggvenn")))

### Parse Arguments ###

args <- commandArgs(trailingOnly = TRUE)

filename <- args[which(args=="--input")+1]
file.out <- args[which(args=="--output")+1]

venn_data <- read.delim(filename,header = FALSE)

colnames(venn_data) <- c("Array","Start","Stop","Tool","x","Index","Cluster_info_1","xx","Cluster_info_2")

tool_names <- data.frame(unique(venn_data$Tool))

x <- list()

for(i in 1:nrow(tool_names)){
  assign(tool_names[i,],as.character(unlist(subset(venn_data,Tool==tool_names[i,])$Index)))

  x[[tool_names[i,]]] <- get(tool_names[i,])  
}

plot_venn <- ggvenn(x,stroke_size = 0.5, set_name_size = 4,fill_color = c("#0073C2FF", "#EFC000FF", "#868686FF", "#CD534CFF"))

pdf(paste0(tools::file_path_sans_ext(file.out),".pdf"))
Sys.sleep(2)
plot_venn
dev.off()

print(paste0("Raw plot is exported as PDF files and can be found in ",getwd()))
       