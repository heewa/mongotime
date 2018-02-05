# Mongotime

[![license](https://img.shields.io/github/license/heewa/mongotime.svg)]()
[![CircleCI](https://img.shields.io/circleci/project/github/heewa/mongotime.svg)]()
[![PyPI](https://img.shields.io/pypi/v/mongotime.svg)]()

Mongotime is a [sampling-based](https://en.wikipedia.org/wiki/Profiling_(computer_programming)#Statistical_profilers) performance analysis tool for MongoDB that aims to give you a deep view into how Mongo is spending its time by showing % utilization of various activity types, and allowing you to add custom grouping and filtering.

This approach is particularly useful if your DB is strained by a high volume of fast queries, rather than a few slow ones. Besides optimizing slow queries, you might want to understand and change general access patterns. For example, maybe your DB is spending way too much time looking up a user's last login time, even if each lookup is very fast because of indexing.

Ex:

```
$ mongotime record --duration 30 recording.mtime  # take a 30 second recording of Mongo DB
...

$ mongotime analyze recording.mtime               # analyze that recording offline

%-of-active-time  %-of-time

client_host:
   50.00%  37.33% - 192.168.1.3
   25.00%  18.24% - 192.168.1.7
    0.99%   0.67% -

collection:
    49.50%  33.33% - users
    49.50%  33.33% - posts
     6.93%   4.67% - $cmd
     3.96%   2.67% -

db:
    99.01%  66.67% - prod
     3.96%   2.67% - test
     0.99%   0.67% - admin

op:
    93.07%  62.67% - update
    93.07%  62.67% - query
     8.91%   6.00% - command
     2.97%   2.00% - insert

user (custom grouping by value of a field in queries):
    14.07%   8.67% - u456
     8.91%   6.00% - u676
     2.97%   2.00% - u935
     0.99%   0.67% - u307

query_keys:
    97.03%  65.33% - {u'email': '*'}
    46.53%  31.33% - {u'_id': '*'}
     0.99%   0.67% - {}
```

## Installing

Currently it's not published to pypi, so you need to install from the repo: `pip install https://github.com/heewa/mongotime/archive/master.zip`, or you can clone the repo and install like `pip install -e .`. This isn't ideal, since you need to uninstall and reinstall to update, but it's temporary. You might want to create and install inside a [virtualenv](https://virtualenv.pypa.io) to make that easier.


## Using

Because mongotime needs to analyze data collected over a period of time, the usage is split into two phases: record & analyze.

### Recording a Trace

Use `mongotime record <optional_filename>` to capture a recording file. Run with `--help` to see options. By default the recording continues until you stop it with `<ctrl>+c`, but you can predefine a duration like `-d 30` (seconds).

I recommend starting with a relatively short duration like 30 seconds, and increasing or decreasing if you want breadth or granularity.

### Analyzing a Recording

Use `mongotime analyze <optional_filename>` to analyze a recording file. At the top of the output you'll see a summary, mainly useful to give a sense of the scope of the recording. Below that you'll see sections of "aspects" of what Mongo is spending its time on, with line items of the top things in that category taking up Mongo's time.

#### Aspects

Operations are grouped together into categories to show "what" the DB is doing. For example, the "collection" grouping will show you what % of time Mongo is spending on ops that are working in each collection shown. The "op" grouping shows how much time is spent on queries vs inserts vs other ops.

#### Understanding % Time Spent

The analysis shows how much time Mongo spends on activities by % activity, like cpu utilization. A value of 50 for `% of time` indicates that for half of the recorded timespan, Mongo was actively working on at least one operation in that grouping. Note: percentages may add to up to greater than 100 - this is because Mongo can simultaneously be working on different operations, and an operation can fall into multiple groupings.

#### Filtering (viewing intersecting aspects)

You can filter ops that go into an analysis as a way of focusing on some slice of activity. For ex, you might want to know what collections a particular client is accessing most, or how much time one collection is spending writing vs reading.

A filter can be specified on the command line as a python statement to be evaluated for each op, where the symbols available are the aspect names (shown as the groupings of rows in an analysis), and their values are the ones shown on rows under an aspect grouping. For ex, `client` is a variable an op has, and `"127.0.0.1:5185"` might be a value. Here are some examples:

* `--filter 'client == "127.0.0.1:57185"'`
* `--filter 'client != "127.0.0.1:57185"'`
* `--filter 'op == "update" and db != "users"'`

_NOTE: during analysis mongotime does not connect to MongoDB._

#### Custom Aspects

There's support for this, but I don't like its usability at the moment. If you want to use this feature, I'd love to hear from you.


## Feedback / Future Development

Got any feedback? Wanna help? Get at me in the Issues or heewa.b@gmail.com!
