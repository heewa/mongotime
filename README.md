[![CircleCI](https://circleci.com/gh/heewa/mongotime.svg?style=svg)](https://circleci.com/gh/heewa/mongotime)

Mongotime is a [sampling-based](https://en.wikipedia.org/wiki/Profiling_(computer_programming)#Statistical_profilers) performance analysis tool for MongoDB that aims to give you a deep view into how Mongo is spending its time. By including all queries, even extremely fast ones, it can show you performance strains on your DB that other tools that focus on slow queries miss.


# Installing

Currently it's not published to pypi, so you need to install from the repo: `pip install https://github.com/heewa/mongotime/archive/master.zip`, or you can clone the repo and install like `pip install -e .`. This isn't ideal, since you need to uninstall and reinstall to update, but it's temporary. You might want to create and install inside a [virtualenv](https://virtualenv.pypa.io) to make that easier.


# Using

Because mongotime needs to analyze data collected over a period of time, the usage is split into two phases: record & analyze.

## Recording a Trace

Use `mongotime record <optional_filename>` to capture a recording file. Run with `--help` to see options. By default the recording continues until you stop it with `<ctrl>+c`, but you can predefine a duration like `-d 30` (seconds).

I recommend starting with a relatively short duration like 30 seconds, and increasing or decreasing if you want breadth or granularity.

## Analyizing a Recording

Use `mongotime analyze <optional_filename>` to analyze a recording file. At the top of the output you'll see a summary, mainly useful to give a sense of the scope of the recording. Below that you'll see sections of "aspects" _(is there a better name for this?)_ of what Mongo is spending its time on, with line tiems of the top things in that category taking up Mongo's time.

Ex output:

```
== Summary ==
  earliest = 1514412554.85
  latest = 1514412569.96
  num_ops = 600
  num_samples = 150
  perc_active = 67.3333333333
  samples_per_sec = 9.92555771762

%-of-active-time  %-of-time

client: (top 5 of 18)
    42.57%  28.67% - 127.0.0.1:57186
    39.60%  26.67% - 127.0.0.1:57185
    39.60%  26.67% - 127.0.0.1:57170
    39.60%  26.67% - 127.0.0.1:57190
    39.60%  26.67% - 127.0.0.1:57191

client_host:
   100.00%  67.33% - 127.0.0.1
     0.99%   0.67% -

collection:
    49.50%  33.33% - Mixed_FindThenUpdate-50-500
    49.50%  33.33% - Mixed_FindOneUpdateIntId-50-500
     6.93%   4.67% - $cmd
     3.96%   2.67% -

db:
    99.01%  66.67% - test0
     3.96%   2.67% -
     0.99%   0.67% - admin

ns:
    49.50%  33.33% - test0.Mixed_FindThenUpdate-50-500
    49.50%  33.33% - test0.Mixed_FindOneUpdateIntId-50-500
     5.94%   4.00% - test0.$cmd
     3.96%   2.67% - None
     0.99%   0.67% - admin.$cmd

op:
    93.07%  62.67% - update
    93.07%  62.67% - query
     8.91%   6.00% - command
     2.97%   2.00% - insert
     0.99%   0.67% - none

query: (top 5 of 250)
    97.03%  65.33% - None
     2.97%   2.00% - {u'_id': 171}
     2.97%   2.00% - {u'x': 212}
     2.97%   2.00% - {u'x': 456}
     1.98%   1.33% - {u'x': 604}

query_keys:
    97.03%  65.33% - None
    46.53%  31.33% - {u'_id': '*'}
    46.53%  31.33% - {u'x': '*'}
     0.99%   0.67% - {}
```

### Aspects 

You can think of an aspect as a type of grouping of Mongo ops, or as a category of "what" the DB is doing. For example, grouping ops by collection will show you what % of time Mongo is spending on ops that are working in each collection shown. The "op" aspect shows how much time is spent on queries vs inserts vs other ops.

### Understanding % Time Spent

There are two columns of %s shown - **% of active time** and **% of time**. They're both a measure of how much of the timespan of the recording (eg the 30 seconds the recording was taken over) that an op had a value show on that row (eg a particular collection, or from some client). You might notice that the %s of multiple items in an aspect (category) can add to greater than 100%. This is because Mongo can simultaneously be working on multiple operations. You might also notice that an aspect that you know has a lot of operations falling under it can have a low % - that's because Mongo might not end up spending that much time actively working on those ops.

The **% of active time** column indicates the % of the time that Mongo was spending doing _anything_ on doing this category of ops. This is useful for Mongo instances that aren't that taxed, so they're rarely doing anything at all, but you'd still like to see "when it does do something, what's it spending most of its time on".

### Filtering (viewing intersecting aspects)

You can filter ops that go into an analysis as a way of focusing on some slice of activity. For ex, you might want to know what collections a particular client is accessing most, or how much time one collection is spending writing vs reading.

A filter can be specified on the command line as a python statement to be evaluated for each op, where the symbols available are the aspect names (shown as the groupings of rows in an analysis), and their values are the ones shown on rows under an aspect grouping. For ex, `client` is a variable an op has, and `"127.0.0.1:5185"` might be a value. Here are some examples:

* `--filter 'client == "127.0.0.1:57185"'`
* `--filter 'client != "127.0.0.1:57185"'`
* `--filter 'op == "update" and db != "users"'`

### Custom Aspects

There's support for this, but I don't like its usability at the moment. If you want to do this, I'd love to hear from you.


# Feedback / Future Development

Got any feedback? Wanna help? Get at me in the Issues or heewa.b@gmail.com!
