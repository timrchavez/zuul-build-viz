#!/usr/bin/env python
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
# Python script for parsing zuul.log and creating charts depicting build
# flow for changes


import argparse
import os
import re
import subprocess
import sys

from datetime import datetime


DT_FMT = "%Y-%m-%d %H:%M:%S.%f"

BASE_ENTRY = (
    "^(?P<dt>\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2},\d{3}) INFO "
)

SCHEDULER_ENTRY = (
    BASE_ENTRY +
    "zuul.Scheduler: " +
    "Adding %s, (?P<change_object><Change 0x[0-9a-f]+ %s>) to <Pipeline %s>$"
)

VERIFIED_REPORTED_ENTRY = (
    BASE_ENTRY +
    "zuul.(Dependent|Independent)PipelineManager: Reporting change %s, " +
    "actions: [<ActionReporter <zuul.reporter.gerrit.Reporter object at " +
    "0x[0-9a-f]+>, {'verified': ((\-2|\-1|1)|2, 'submit': True)}>]"
)

BUILD_STARTED_ENTRY = (
    BASE_ENTRY +
    "zuul.(Dependent|Independent)PipelineManager: Reporting start, " +
    "action [<ActionReporter <zuul.reporter.gerrit.Reporter object " +
    "at 0x[0-9a-f]+>, {'verified': 0}>] change %s"
)

JOB_LAUNCH_JOB_ENTRY = (
    BASE_ENTRY +
    "zuul.Gearman: Launch job (?P<job>[\w\-]+) \(uuid: (?P<uuid>\w+)\) for " +
    "change %s with dependent changes"
)

JOB_START_ENTRY = (
    BASE_ENTRY +
    "zuul.Gearman: Build <gear.Job 0x[0-9a-f]+ handle: H:127.0.0.1:\d+ " +
    "name: build:[\w\-]+ unique: (?P<uuid>\w+)> started"
)

JOB_COMPLETE_ENTRY = (
    BASE_ENTRY +
    "zuul.Gearman: Build <gear.Job 0x[0-9a-f]+ handle: H:127.0.0.1:\d+ " +
    "name: build:[\w\-]+ unique: (?P<uuid>\w+)> complete, result " +
    "(SUCCESS|FAILURE|NOT_REGISTERED|None)"
)


class Record(object):

    def __init__(self, change_object, queued):
        self.change_object = change_object
        self.jobs = {}
        self.build_started = None
        self.build_completed = None
        self.first_job_submitted = None
        self.last_job_completed = None
        self.queued = queued


def create_chart_table(record, filename):
    with open(filename, "w") as f:
        f.write("event;start;end;delta;color_group\n")
        if record.queued and record.build_started:
            dt1 = datetime.strptime(record.queued, DT_FMT)
            dt2 = datetime.strptime(record.build_started, DT_FMT)
            delta = (dt2-dt1).total_seconds()
            f.write("change queued;{0};{1};{2};1\n".format(
                record.queued, record.build_started, delta))
        elif not record.queued:
            sys.exit("E: Change queued time is not set")
        elif not record.build_started:
            sys.exit("E: Build started time is not set")
        if record.build_started and record.first_job_submitted:
            dt1 = datetime.strptime(record.build_started, DT_FMT)
            dt2 = datetime.strptime(record.first_job_submitted, DT_FMT)
            delta = (dt2-dt1).total_seconds()
            f.write("build started;{0};{1};{2};2\n".format(
                record.build_started, record.first_job_submitted, delta))
        elif not record.first_job_submitted:
            sys.exit("E: First job submitted time is not set")
        count = 3
        for uuid, job in record.jobs.iteritems():
            if job["launch"] and job["job_start"]:
                dt1 = datetime.strptime(job["launch"], DT_FMT)
                dt2 = datetime.strptime(job["job_start"], DT_FMT)
                delta = (dt2-dt1).total_seconds()
                f.write("build:{0} submitted;{1};{2};{3};{4}\n".format(
                    job["name"], job["launch"], job["job_start"], delta,
                    count))
            elif not job["launch"]:
                sys.exit("E: Job submitted time is not set")
            elif not job["job_start"]:
                sys.exit("E: Job started time is not set")
            if job["job_start"] and job["job_complete"]:
                dt1 = datetime.strptime(job["job_start"], DT_FMT)
                dt2 = datetime.strptime(job["job_complete"], DT_FMT)
                delta = (dt2-dt1).total_seconds()
                f.write("build:{0} building;{1};{2};{3};{4}\n".format(
                    job["name"], job["job_start"], job["job_complete"],
                    delta, count))
            elif not job["job_complete"]:
                sys.exit("E: Job completed time is not set")
            count += 1

        if record.last_job_completed and record.build_completed:
            dt1 = datetime.strptime(record.last_job_completed, DT_FMT)
            dt2 = datetime.strptime(record.build_completed, DT_FMT)
            delta = (dt2-dt1).total_seconds()
            f.write("build completed;{0};{1};{2};{3}\n".format(
                record.last_job_completed, record.build_completed,
                delta, count))
        elif record.last_job_completed:
            sys.exit("E: Last job submitted time is not set")
        elif record.build_completed:
            sys.exit("E: Build completed time is not set")

    print "Wrote: %s" % filename


def create_chart_image(record, data_filename, image_filename, title):
    p = subprocess.Popen(
        ["./timeline.R",
         "data_filename='%s'" % data_filename,
         "image_filename='%s'" % image_filename,
         "title='%s'" % title],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if p.returncode != 0:
        sys.exit("Graph generation failed!\nOUTPUT:\n%s" % stderr)

    print "Wrote: %s" % image_filename


def get_log_lines(log_path, start_time=None):
    if start_time:
        start_dt = datetime.strptime(start_time.replace(",", "."), DT_FMT)
    with open(log_path) as log:
        for line in log.readlines():
            match = re.match(BASE_ENTRY + ".*", line)
            if match:
                dt = datetime.strptime(
                    match.group("dt").replace(",", "."), DT_FMT)
                if start_time and dt < start_dt:
                    continue
                yield line


def get_change_record(log_path, project, change, pipeline,
                      start_time=None):
    record = None
    for line in get_log_lines(log_path, start_time):
        match = re.match(SCHEDULER_ENTRY % (project, change, pipeline), line)
        if match:
            dt = match.group("dt").replace(",", ".")
            if record and record.queued:
                break
            record = Record(match.group("change_object"), dt)
        if record:
            verified_entry = (
                BUILD_STARTED_ENTRY % record.change_object)
            match = re.match(verified_entry, line)
            if match:
                dt = match.group("dt").replace(",", ".")
                record.build_started = dt
            verified_entry = (
                VERIFIED_REPORTED_ENTRY % record.change_object)
            match = re.match(verified_entry, line)
            if match:
                dt = match.group("dt").replace(",", ".")
                record.build_completed = dt
                break
            match = re.match(
                JOB_LAUNCH_JOB_ENTRY % record.change_object, line)
            if match:
                dt = match.group("dt").replace(",", ".")
                record.jobs[match.group("uuid")] = {
                    "name": match.group("job"),
                    "launch": dt,
                    "job_start": None,
                    "job_complete": None
                }
                if record.first_job_submitted:
                    dt1 = datetime.strptime(record.first_job_submitted, DT_FMT)
                    dt2 = datetime.strptime(dt, DT_FMT)
                    if dt1 > dt2:
                        record.first_job_submitted = dt2.strftime(DT_FMT)
                else:
                    record.first_job_submitted = dt
            match = re.match(JOB_START_ENTRY, line)
            if match and match.group("uuid") in record.jobs:
                dt = match.group("dt").replace(",", ".")
                record.jobs[match.group("uuid")]["job_start"] = dt
            match = re.match(JOB_COMPLETE_ENTRY, line)
            if match and match.group("uuid") in record.jobs:
                dt = match.group("dt").replace(",", ".")
                record.jobs[match.group("uuid")]["job_complete"] = dt
                if record.last_job_completed:
                    dt1 = datetime.strptime(
                        record.last_job_completed, DT_FMT)
                    dt2 = datetime.strptime(dt, DT_FMT)
                    if dt1 < dt2:
                        record.last_job_completed = dt2.strftime(DT_FMT)
                else:
                    record.last_job_completed = dt

    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-filename", default="change.csv",
        help="The chart data filename")
    parser.add_argument(
        "--image-filename", default="change.png",
        help="The chart image filename")
    parser.add_argument(
        "--log-path", default="/var/log/zuul/zuul.log",
        help="Full path to log file to analyze")
    parser.add_argument(
        "--start-time",
        help="Start time in log to look for change")
    parser.add_argument(
        "project",
        help="Gerrit Project (e.g. hp/config)")
    parser.add_argument(
        "change",
        help="Gerrit Change ID and patch # (e.g. 12345,1)")
    parser.add_argument(
        "pipeline",
        help="Zuul pipeline (e.g. check)")
    args = parser.parse_args()

    if not os.path.exists(args.log_path):
        sys.exit("E: Could not find log at '%s'" % args.log_path)
    record = get_change_record(
        args.log_path, args.project, args.change, args.pipeline,
        args.start_time)
    if not record:
        sys.exit("E: Change with those parameters was not found!")

    create_chart_table(
        record,
        args.data_filename
    )

    create_chart_image(
        record,
        args.data_filename,
        args.image_filename,
        "%s %s %s" % (args.project, args.change, args.pipeline))


if __name__ == "__main__":
    main()
