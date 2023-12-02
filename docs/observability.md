Observability
=============

This page describes **how to monitor the Gameserver with dashboards, metrics, and logs**.

Built-In Dashboards
-------------------
CTF Gameserver's Web component includes several dashboards for service authors to observe the behavior of
their Checker Scripts:

* **Service History** shows the check results for all teams over multiple ticks. It provides a nice overview
  of the Checker Script's behavior at large.
* **Missing Checks** lists checks with the "Not checked" status. These are particularly interesting because
  they point at crashes or timeouts.

Access to all of these requires a user account with "Staff" status. If configured, links to the corresponding
logs in Graylog are automatically generated (setting `GRAYLOG_SEARCH_URL`).

Users with "Staff" status can also view the **VPN Status History** dashboard of any selected team.

Logging
-------
All components write logs to stdout, from where they are usually picked up by systemd. You can view them
through the regular journald facilities (`journalctl`).

The only exception to this are Checker Script logs, which can be very verbose and should be accessible to
their individual authors.

### Checkers
You must explicitly configure Checker Script logs to be sent to either journald or Graylog.

[Graylog (Open)](https://graylog.org/products/source-available/) is the recommended option, especially for
larger competitions. It allows logs to be accessed through a web interface and filtered by service, team,
tick, etc. When `GRAYLOG_SEARCH_URL` is configured for the Web component, the built-in dashboards
automatically generate links to the respective logs.

After installing Graylog, create a new "GELF UDP" input through the web interface with a large enough
`recv_buffer_size` (we use 2 MB, i.e. 2097152 bytes). The parameters of this input then get used in the
`CTF_GELF_SERVER` option.

With journald-based Checker logging, you can filter log entries like this:

    journalctl -u ctf-checkermaster@service.service SYSLOG_IDENTIFIER=checker_service-team023-tick042

Additionally, the `ctf-logviewer` script is available. It is designed to be used as an SSH `ForceCommand` to
give service authors access to logs for a specific service.

Metrics
-------
All components except Web can expose metrics in [Prometheus](https://prometheus.io/) format. Prometheus
enables both alerting and dashboarding with [Grafana](https://grafana.com/grafana/).

To enable metrics, configure `CTF_METRICS_LISTEN` (the Ansible roles do that by default). For the available
metrics and their description, manually request the metrics via HTTP.
