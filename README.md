Zuul Build Visualizations
=========================

This is a profiling tool for changeset builds in an #Openstack CI workflow.
It parses the zuul.log file for build event information related to a specific
changeset build.  While looking at the aggregate times of such events is
indeed useful (and pertinent), so can profiling a single build.  Often times
a user of the CI system wants to know where all the time is going for a
particular changeset build in their project.  While it cannot give the user
the complete story, it can nicely summarize it, and give them some answers and
places to look for improvement.  It can also be useful to an operator or admin
looking into specific performance issues affecting users.

To get a better idea of what I'm talking about, check out this sample chart:

http://i.imgur.com/0craBhV.png

Requirements
============
  * Ubuntu 14.04 (Trusty)
  * r-base-core >=3.0.2-1ubuntu1
  * r-cran-ggplot2 >=0.9.3.1-1
  * python2.7 =2.7.6-8ubuntu0.2

Install
=======

Currently there is no Python package to build and install.  It's just a
standalone script.

```
# sudo apt-get update
# sudo apt-get -y install python2.7 r-base-core r-cran-ggplot2
```
Examples
========

```
# zuul_build_viz.py --log-path=/path/to/zuul.log --start-time="2015-07-10 16:04:30,133" openstack-infra/zuul 12345,1 gate
Wrote: change.csv
Wrote: change.png

# zuul_build_viz.py --data-filename="data.csv" --image-filename="chart.png" openstack-infra/zuul 12345,1 gate
Wrote: data.csv
Wrote: chart.png
```

Caveats
=======

 * The same change can appear multiple times in the log.  If you do not
   not specify a "--start-time" on the command line, the first instance of a
   change will always be used
 * Changes of the type NullChange cannot be visualized.  This generally means
   that periodic builds cannot be visualized with this tool.  Sorry!
 * Merge events are not tied to changes in the log, so they cannot (yet) be
   depicted
