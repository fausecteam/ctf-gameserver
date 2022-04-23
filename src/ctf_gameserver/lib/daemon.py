import logging


def notify(*args, **kwargs):

    try:
        import systemd.daemon    # pylint: disable=import-outside-toplevel
        systemd.daemon.notify(*args, **kwargs)
    except ImportError:
        logging.info('Ignoring daemon notification due to missing systemd module')
