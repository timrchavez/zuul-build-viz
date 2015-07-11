#!/usr/bin/Rscript
# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# R script for generating a timeline of a change build

library("ggplot2")
library("scales")

# Default settings
title = "unset title"
data_filename = "graph.csv"
image_filename = "graph.png"

# Override default settings
args <- commandArgs(trailingOnly = TRUE)
for(i in 1:length(args)){
    eval(parse(text=args[i]))
}

# Create data frame from data table
df <- read.csv2(data_filename)
df$start <- as.POSIXct(strftime(df$start, "%Y-%m-%d %H:%M:%OS3"))
df$end <- as.POSIXct(strftime(df$end, "%Y-%m-%d %H:%M:%OS3"))
# HACK: Enforce ordering on Y-axis
df$event <- as.character(df$event)
df$event <- factor(df$event, levels=rev(unique(df$event)))

# Create the limits of a datetime continuum
limits <- c(head(df, 1)$start, tail(df,1)$end)

# HACK: Prevent empty Rplot.pdf from being generated
options(device="png")
par()
dev.off()

# Color palette
colfunc<-colorRampPalette(c("red","yellow","springgreen","royalblue"))

# Generate plot
p <- ggplot(df, aes(colour=color_group)) +
       ggtitle(title) +
       xlab("time between events") +
       theme_minimal() +
       theme(text=element_text(colour="white"),
             axis.text.x=element_text(angle=90, vjust=0.5, hjust=1), legend.position="none",
             plot.background=element_rect(fill = "black"), panel.background=element_rect(fill="black", colour="white"),
             panel.grid.major = element_blank(), panel.grid.minor = element_blank()) +
       scale_colour_gradientn(colours=colfunc(tail(df,1)$color)) +
       scale_x_datetime(breaks=date_breaks("1 min"), minor_breaks=date_breaks("30 sec"), limits=limits) +
       geom_segment(aes(x=start, xend=end, y=event, yend=event), size=2) +
       geom_point(aes(x=start,y=event), shape=15, size=4) +
       geom_point(aes(x=end,y=event), shape=15, size=4) +
       geom_text(aes(x=end, y=event, label=delta), size=4, hjust=-0.25) +
       ggsave(image_filename, width=20, height=10, dpi=300)
