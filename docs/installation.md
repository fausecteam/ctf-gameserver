Installation
============

For a small competition, it can be sufficient to deploy all CTF infrastructure on a single host. If your
competition is larger, you should distribute CTF Gameserver's components over several machines.

Some recommendations on that with regard to CPU, memory, and disk requirements…

… for external requirements:

* From our experience, CTF Gameserver does not put a high load on the **Postgres database**. A small to
  medium-sized machine should be sufficient as database server.
* **VPN/router machines** have rather high requirements. It can make sense to run multiple of them and shard
  teams among them.

… for CTF Gameserver components:

* The **Controller** can reasonably be colocated on the database server, as its requirements are quite low.
* **Submission** has relatively low requirements. In small to medium-sized setups, colocating it with
  database and Controller should suffice. In larger setups, one small machine should be enough, but multiple
  machines are still possible.
* The **Web** component scales like a typical Django-based web app. If you get more requests, it makes sense
  to use a separate, more powerful host. You could also run multiple application servers, but we never felt
  the need to do so.
* The requirements of the **Checkers** drastically depend on the behavior of your individual Checker scripts.
  It usually makes sense to scale Checkers by running them on multiple powerful machines.
* If you use the **VPN Status** component, the collection helper must run on your VPN/router machines.

Package Build
-------------
The recommended installation method for CTF Gameserver is through a Debian package. We do not provide
pre-built packages, which gives you the option to apply all kinds of adjustments before building a package.

To get a package, clone [CTF Gamesever's repository](https://github.com/fausecteam/ctf-gameserver) to a
Debian-based host. There are no releases, but the "master" branch should always be in a usable state.

The build commands are:

    $ git clone git@github.com:fausecteam/ctf-gameserver.git
    $ cd ctf-gameserver
    # Do custom adjustments if desired
    $ sudo apt install devscripts dpkg-dev equivs
    $ sudo mk-build-deps --install debian/control
    $ dpkg-buildpackage --unsigned-changes --unsigned-buildinfo

This should result in a package file called `ctf-gameserver_1.0_all.deb` **in the parent directory**.

All components get installed from this same Debian package, but none of them are activated upon installation.
You control what gets run where, by starting the corresponding systemd units (or configuring a web
application server).

Ansible
-------
The recommended way to install and configure CTF Gameserver is to use our Ansible roles provided in
[CTF Gameserver Ansible](https://github.com/fausecteam/ctf-gameserver-ansible).

For instructions on how to use these roles, please refer to that repo's README file. The roles will install a
PostgreSQL server from the Debian repositories and set up the Gameserver database.

Configuration
-------------
### General
Configuration for the components is either provided through command-line arguments or equivalent environment
variables. The Debian package already installs minimal environment files with dummy values to
`/etc/ctf-gameserver`, from where they get picked up by the systemd units.

You can get help on the individual options by invoking CTF Gameserver's executables with the `--help` option
(`ctf-controller --help`, `ctf-submission --help`, etc.).

When using the Ansible roles, options in the environment files get set from the respective Ansible variables.

### Submission
The Submission server runs an event loop and is single-threaded. To make use of multiple CPU cores, you
need to run multiple instances.

To support that need, the submission systemd service is an
[instantiated unit](https://0pointer.de/blog/projects/instances.html).
The instance name (the part after the '@') controls the name of an additional environment file
(`/etc/ctf-gameserver/submission-<name>.env`). This can be used to run multiple instances on different ports.

The Ansible role will already create one instance with an associated environment file per port listed in
`ctf_gameserver_submission_listen_ports`.

To still provide a single submission port to teams, you may use iptables rules like these (assuming four instances):

    $ iptables -t nat -A PREROUTING -p tcp --dport 666 -m state --state NEW -m statistic --mode nth --every 4 --packet 0 - j DNAT --to-destination :6666
    $ iptables -t nat -A PREROUTING -p tcp --dport 666 -m state --state NEW -m statistic --mode nth --every 3 --packet 0 - j DNAT --to-destination :6667
    $ iptables -t nat -A PREROUTING -p tcp --dport 666 -m state --state NEW -m statistic --mode nth --every 2 --packet 0 - j DNAT --to-destination :6668
    $ iptables -t nat -A PREROUTING -p tcp --dport 666 -m state --state NEW -m statistic --mode nth --every 1 --packet 0 - j DNAT --to-destination :6669

### Checkers
Checkers use an instantiated systemd unit with a Checker Master instance per service. The Ansible role will
**not** configure or start these instances.

A typical service-specific environment file in `/etc/ctf-gameserver/checker/<service>.env` will look like
this:

    CTF_SERVICE="service-slug"
    CTF_CHECKERSCRIPT="/path/to/service-script"
    CTF_CHECKERCOUNT="1"
    CTF_INTERVAL="10"

There may be multiple Master instances for each service (usually on separate hosts). `CTF_CHECKERCOUNT` must
be set to the total number of Master instances for the service. `CTF_INTERVAL` is the time between launching
batches of Checker Scripts in seconds and should be considerably shorter than the tick length.

You need to explicitly configure an output for Checker Scripts logs using either the `CTF_JOURNALD` or the
`CTF_GELF_SERVER` (Graylog) option. Larger setups should use Graylog as it can handle a larger volume of
log entries. See the [docs on Checker logging](observability.md#checkers) for details.

### Web
#### Application Server
To run the Web component, you will need a WSGI application server such as Gunicorn or uWSGI. Please refer
to [Django's instructions on how to deploy with WSGI](https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/).

The Web component uses Django's settings mechanism instead of the environment files described above. Its
config file is located at `/etc/ctf-gameserver/web/prod_settings.py`. When using the Ansible role, that
file gets generated from an Ansible template.

The WSGI module for CTF Gameserver is called `ctf_gameserver.web.wsgi:application`. To pick up the
configuration file, `/etc/ctf-gameserver/web` must be on the PYTHONPATH and the environment variable
`DJANGO_SETTINGS_MODULE` must be set to `prod_settings`.

Example config for uWSGI, using Debian packages `uwsgi` and `uwsgi-plugin-python3`:

    [uwsgi]
    plugins = python3
    uwsgi-socket = /run/uwsgi/ctf-gameserver.sock
    python-path = /etc/ctf-gameserver/web
    module = ctf_gameserver.web.wsgi:application
    env = DJANGO_SETTINGS_MODULE=prod_settings
    master = True
    vacuum = True

Medium-sized or larger setups should utilize [Django’s cache framework](https://docs.djangoproject.com/en/4.2/topics/cache/).
We recommend [using Memcached](https://docs.djangoproject.com/en/4.2/topics/cache/#memcached) with
`django.core.cache.backends.memcached.PyMemcacheCache`. Memcached's memory limits should be increased by
setting `-m 256` and `-I 5m`.

#### Static Files
In addition to the application server, some static files need to be delivered through a web server (e.g. one
that also acts as reverse proxy for the application). An example nginx config snippet would look like this:

    location /static/ {
        alias /usr/lib/python3/dist-packages/ctf_gameserver/web/static/;
    }
    location /static/admin/ {
        root /usr/lib/python3/dist-packages/django/contrib/admin/;
    }
    location /uploads/ {
        alias /var/www/gameserver_uploads/;
        # Prevent any JS execution from user uploads as a defense-in-depth measure
        add_header Content-Security-Policy "default-src 'none'";
    }
    location = /robots.txt {
        alias /usr/lib/python3/dist-packages/ctf_gameserver/web/static/robots.txt;
    }

!!! warning

    Using the nginx `add_header` directive within a `location` block will clear **any** other headers set in
    outer blocks. Repeat those headers in the `location` block or switch all of your nginx header handling to
    [ngx_headers_more](https://github.com/openresty/headers-more-nginx-module).

Manual Database Setup (without Ansible)
---------------------------------------
If you are **not using our Ansible roles**, you need to manually install PostgreSQL and set up the database.

1. Create a Postgres user and a database owned by it. Add these parameters to
   `/etc/ctf-gameserver/web/prod_settings.py`.
2. `PYTHONPATH=/etc/ctf-gameserver/web DJANGO_SETTINGS_MODULE=prod_settings django-admin migrate auth`
3. `PYTHONPATH=/etc/ctf-gameserver/web DJANGO_SETTINGS_MODULE=prod_settings django-admin migrate`
4. To create an initial admin user for the Web component, run:
   `PYTHONPATH=/etc/ctf-gameserver/web DJANGO_SETTINGS_MODULE=prod_settings django-admin createsuperuser`

If you want to restrict database access for the individual roles to what is actually required, create
additional Postgres users with the respective database grants. For details, see the [tasks from the
"db_epilog" Ansible role](https://github.com/fausecteam/ctf-gameserver-ansible/blob/master/roles/db_epilog/tasks/main.yml).

Gameserver Setup
----------------
After setting up the database and the web component, visit your website. It is expected that the start page
will show error 404, as no content has been created yet. Instead, visit the `/admin` path and log in with
your web credentials (Ansible vars `ctf_gameserver_web_admin_user` & `ctf_gameserver_web_admin_pass`).

To configure the basic parameters of your competition, click "Game control" (under "SCORING"). Afterward,
add your services. There is no need to touch "Captures", "Flags", "Status checks", or "VPN status checks".

You can use "Flatpages" to provide static web content. By default, each category will result in a dropdown
menu in the main navigation. For the home page, create a page with an empty title and no category.

Personal files (e.g. VPN configs or other credentials) can be provided to teams confidentially through the
"Team Downloads" feature. To use it, set up `TEAM_DOWNLOADS_ROOT` in `prod_settings.py` and set up the
file names and descriptions through the admin interface. The per-team files then must be copied to the
filesystem hierarchy below `TEAM_DOWNLOADS_ROOT`, see the comment in `prod_settings.py` for details.
