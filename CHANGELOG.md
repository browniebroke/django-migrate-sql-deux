# Changelog

<!-- version list -->

## v1.0.1 (2025-04-14)

### Bug Fixes

- Run Ruff with unsafe fixes
  ([`45a85b2`](https://github.com/browniebroke/django-migrate-sql-deux/commit/45a85b253ba92f9da37645177b5668f908261fa2))

### Testing

- Tidy up and simplify test settings
  ([`affbd00`](https://github.com/browniebroke/django-migrate-sql-deux/commit/affbd00ae82cf90d2d46d9a75e9fa8f9c157caa8))


## v1.0.0 (2025-04-14)

### Bug Fixes

- Update PSR config to fix automated releases
  ([`5c77f58`](https://github.com/browniebroke/django-migrate-sql-deux/commit/5c77f58f673a1ed883b91f169a033285f7b81f00))

### Features

- Migrate to pyproject.toml
  ([`2d3c547`](https://github.com/browniebroke/django-migrate-sql-deux/commit/2d3c5476f72c67b9c49863fde6e3e53939ac0150))

BREAKING CHANGE: drop support for Django <4.2

### Refactoring

- Rename package to django_migrate_sql
  ([`c3bc1df`](https://github.com/browniebroke/django-migrate-sql-deux/commit/c3bc1df60e1c7580666f6978025391f2a279d3fd))

BREAKING CHANGE: rename package from `migrate_sql` to `django_migrate_sql` to follow Django reusable
  apps best practices

### Testing

- Re-organise test project
  ([`3417b0f`](https://github.com/browniebroke/django-migrate-sql-deux/commit/3417b0f6ae966fa4c89703facd04da09375fe2fa))

- Update tox file to run with uv
  ([`479a0af`](https://github.com/browniebroke/django-migrate-sql-deux/commit/479a0af2a294256980513a6e40cd1cc56ac3a52b))

### Breaking Changes

- Drop support for Django <4.2

- Rename package from `migrate_sql` to `django_migrate_sql` to follow Django reusable apps best
  practices


## v0.7.0 (2025-04-12)

### Features

- Add support for Django 4.1
  ([`53997f6`](https://github.com/browniebroke/django-migrate-sql-deux/commit/53997f65961c0f1b36d124432f496cbb1725e988))

- Add support for Django 4.2
  ([`a1599ec`](https://github.com/browniebroke/django-migrate-sql-deux/commit/a1599ec5e836140e2c1d035af29dcc604c63b6aa))

- Add support for Django 5.0
  ([`97faea1`](https://github.com/browniebroke/django-migrate-sql-deux/commit/97faea1a495638899a0ba05628c47cc9edba5824))

- Add support for Django 5.1
  ([`46bce08`](https://github.com/browniebroke/django-migrate-sql-deux/commit/46bce08a4ae020015594645a42b100f8ca71db96))

- Add support for Django 5.2
  ([`dd49703`](https://github.com/browniebroke/django-migrate-sql-deux/commit/dd4970395d58099a77cb5eb5307a266c5ee61005))

- Add support for Python 3.11
  ([`aa4549c`](https://github.com/browniebroke/django-migrate-sql-deux/commit/aa4549caacce7a83db8ff9997f96d1163934eb18))

- Add support for Python 3.12
  ([`3c8472f`](https://github.com/browniebroke/django-migrate-sql-deux/commit/3c8472f24fbf06606a770b120beaa437e0d5070f))

- Add support for Python 3.13
  ([`22d9078`](https://github.com/browniebroke/django-migrate-sql-deux/commit/22d90784e179f885b87b617ffdcf46abbc9a1664))

- Drop support for Django <3.2
  ([`35e90d8`](https://github.com/browniebroke/django-migrate-sql-deux/commit/35e90d8f3911d25f03df7d3f13b4a1b667ddfe06))

- Drop support for Python <3.9
  ([`73252f3`](https://github.com/browniebroke/django-migrate-sql-deux/commit/73252f333b4b87c1f0586874039d74b523e88580))


## v0.6.0 (2025-04-11)

### Bug Fixes

- Add missing long_description_content_type to setup call
  ([`eb96c57`](https://github.com/browniebroke/django-migrate-sql-deux/commit/eb96c57f29deb26fa98645abb0f9ca2f6f66abe2))

### Features

- Add support for Django 3.1
  ([`f9ad68e`](https://github.com/browniebroke/django-migrate-sql-deux/commit/f9ad68e1ed30da2f2b583a2bac953a3ff43c878b))

- Add support for Django 3.2
  ([`660e924`](https://github.com/browniebroke/django-migrate-sql-deux/commit/660e924a999244529964646388014fef78148226))

- Add support for Django 4.0
  ([`73c3743`](https://github.com/browniebroke/django-migrate-sql-deux/commit/73c374364745d957d60973d2e7c33cce3b12915b))

- Add support for Python 3.10
  ([`0e8ac4d`](https://github.com/browniebroke/django-migrate-sql-deux/commit/0e8ac4ddb42325f13eb4366f569eb376a7fa652a))

- Add support for Python 3.8 and 3.9
  ([`e557917`](https://github.com/browniebroke/django-migrate-sql-deux/commit/e557917ceb37a91d260a367b56408dd62df9f5c4))


## v0.5.3 (2025-04-11)

### Bug Fixes

- Update project URL and update README
  ([#6](https://github.com/browniebroke/django-migrate-sql-deux/pull/6),
  [`1d41ba8`](https://github.com/browniebroke/django-migrate-sql-deux/commit/1d41ba8e14fa1929ce656de44b12b1458b0ebeeb))


## v0.5.2 (2025-04-11)

### Bug Fixes

- Add build command to fix automatic release
  ([#5](https://github.com/browniebroke/django-migrate-sql-deux/pull/5),
  [`9568a7f`](https://github.com/browniebroke/django-migrate-sql-deux/commit/9568a7f499ad6e3733d2249c9f7da0fefd986e38))


## v0.5.1 (2025-04-11)

### Bug Fixes

- Migrate CI to GitHub actions and automate release using Python Semantic Release
  ([#4](https://github.com/browniebroke/django-migrate-sql-deux/pull/4),
  [`5cab3bf`](https://github.com/browniebroke/django-migrate-sql-deux/commit/5cab3bf94d3df000d8140f1da108117d0e2ded69))


## v0.5.0 (2020-03-31)

### Features

- Drop support for Django 2.0

### Bugfixes

- Disable translations while making migrations

## v0.4.0 (2020-03-27)

### Features

- Add support for Django 3.0

### Clean-up

- Cleanup Python 2 future imports
- Remove django.utils.six import
