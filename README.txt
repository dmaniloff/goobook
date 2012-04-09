:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
GooBook -- Access your Google contacts from the command line.
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

.. contents:: **Table of Contents**

About
=====

The purpose of GooBook is to make it possible to use your Google Contacts from
the command-line and from MUAs such as Mutt.
It can be used from Mutt the same way as abook.

Installation Instructions
=========================

There is a number of ways to install Python software.

- Using pip
- Using easy_install
- Using a source tarball
- Using source directly from gitorius
- From a distribution specific repository (Arch Linux AUR)

pip or easy_install
-------------------

This is the recommended way to install goobook for most users.
When installing this way you will not need to download anything manually.

Run pip or easy_install::

    $ pip install goobook
    $ easy_install -U goobook

easy_install is part of setuptools which should come with most distributions,
pip is a newer replacement.

Source installation
-------------------

Download the source tarball, uncompress it, then run the install command::

    $ tar -xzvf goobook-*.tar.gz
    $ cd goobook-*
    $ sudo python ./setup.py install

Upgrading from < 1.0
--------------------

If you are upgrading from a pre 1.0 version you will have to remove the old
cachefile and create a new configuration.

Configure
=========

For most users it will be enough to add an entry to your ~/.netrc::

    machine google.com
      login your@google.email
      password secret

NOTE: The netrc implementation in Python don't support passwords with spaces, use the .goobookrc or keyring instead.

To get access too more settings you can create a configuration file::

    goobook config-template > ~/.goobookrc

It will look like this::

    # "#" or ";" at the start of a line makes it a comment.
    [DEFAULT]
    # If not given here, email and password is taken from .netrc using
    # machine google.com
    ;email: user@gmail.com
    ;password: top secret
    # or if you want to get the password from a commmand:
    ;passwordeval: gpg --batch -d ~/.mutt/pw.gpg
    # The following are optional, defaults are shown
    ;cache_filename: ~/.goobook_cache
    ;cache_expiry_hours: 24


If you set the password to "prompt" you will be prompted each time the password is needed
but this does not work well with mutt.

Instead of being a plain config file ``.goobookrc`` can be an executable,
in which case it's output will be used as configuration.

For example if you want to store your configuration encrypted with GnuPG as ``.goobookrc.gpg``
you can use a ``.goobookrc`` like this::

    #!/bin/sh
    gpg --no-tty --use-agent -q -d ~/.goobookrc.gpg

You will need to have a appropriate gpg-agent/pinentry setup, you will not be prompted
for the gpg passphrase on the console.

Similarly, goobook supports authentication by keyring_. The keyring package
supports multiple backends, depending on your
environment. You should configure it to point to the one you're using by
default. To use this option, set your e-mail address in the config file but
leave the password field commented out (or blank). You need to have a password
for the "gmail" service and your e-mail address stored in the keyring. There
are several ways to achieve this, here is one::

    $ python
    >>> import keyring
    >>> keyring.set_password("gmail", "me@example.com", "secret")

.. _keyring: http://pypi.python.org/pypi/keyring

Proxy settings
--------------

If you use a proxy you need to set the https_proxy environment variable.

Mutt
----

If you want to use goobook from mutt.

Set in your .muttrc file::

    set query_command="goobook query '%s'"

to query address book. (Normally bound to "Q" key.)

If you want to be able to use <tab> to complete email addresses instead of Ctrl-t add this:

    bind editor <Tab> complete-query

To add email addresses (with "a" key normally bound to create-alias command)::

    macro index,pager a "<pipe-message>goobook add<return>" "add the sender address to Google contacts"

If you want to add an email's sender to Contacts, press a while it's selected in the index or pager.

Usage
=====

To query your contacts::

    $ goobook query QUERY

The add command reads a email from STDIN and adds the From address to your Google contacts::

    $ goobook add

The cache is updated automatically according to the configuration but you can also force an update::

    $ goobook reload

For more commands see::

    $ goobook -h

and::

    $ goobook COMMAND -h

Links, Feedback and getting involved
====================================

- Home page: http://code.google.com/p/goobook
- PyPI home: http://pypi.python.org/pypi/goobook
- Mailing list: http://groups.google.com/group/goobook
- Issue tracker: http://code.google.com/p/goobook/issues/list
- Code Repository: http://gitorious.org/goobook

