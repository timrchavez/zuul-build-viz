Zuul Build Visualizations
=========================

This tool parses the zuul.log file, looking for events related to a specific
changeset (that you specify) and when they happen.  Using this data, a chart
is created depicting the transition time between events.  These charts can
give us a very nice picture of where all the time is spent during a build,
including insights into interesting behavior (such as a job being rescheduled
or an abnormally long wait time between the time a job is submitted and when
it starts to build).

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
