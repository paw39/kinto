"""
A helper class to run migrations using a series of SQL files.
"""

import logging
import os

logger = logging.getLogger(__name__)


class Migrator(object):
    """Mixin to allow the running of migrations."""

    """Name of this migrator (e.g. "storage"). Override this."""
    name = None

    """The current "newest" schema version. Override this."""
    schema_version = None

    """The file to find the current "newest" schema in. Override this."""
    schema_file = None

    """The directory to find migration files in.

    Migrations should each be a file named migration_nnn_mmm.sql, where mmm = nnn + 1.
    """
    migrations_directory = None

    def _get_installed_version(self):
        """Return current version of schema or None if none found.

        Override this.

        This may be called several times during a single migration.
        """
        pass

    def create_or_migrate_schema(self, dry_run=False):
        """Either create or migrate the schema, as needed."""
        version = self._get_installed_version()
        if not version:
            self.create_schema(dry_run)
            return

        logger.info('Detected PostgreSQL {} schema version {}.'.format(self.name, version))
        if version == self.schema_version:
            logger.info('PostgreSQL {} schema is up-to-date.'.format(self.name))
            return

        self.migrate_schema(version, dry_run)
        return

    def create_schema(self, dry_run):
        """Actually create the schema from scratch using self.schema_file.

        You can override this if you want to add additional sanity checks.
        """
        logger.info('Create PostgreSQL {} schema at version {} from {}'.format(
            self.name, self.schema_version, self.schema_file))
        if not dry_run:
            self._execute_sql_file(self.schema_file)
            logger.info('Created PostgreSQL {} schema (version {}).'.format(
                self.name, self.schema_version))

    def migrate_schema(self, start_version, dry_run):
        migrations = [(v, v + 1) for v in range(start_version, self.schema_version)]
        for migration in migrations:
            expected = migration[0]
            current = self._get_installed_version()
            error_msg = 'PostgreSQL {} schema: Expected version {}. Found version {}.'
            if not dry_run and expected != current:
                raise AssertionError(error_msg.format(self.name, expected, current))

            logger.info('Migrate PostgreSQL {} schema from version {} to {}.'.format(
                self.name, *migration))
            filename = 'migration_{0:03d}_{1:03d}.sql'.format(*migration)
            filepath = os.path.join(self.migrations_directory, filename)
            logger.info('Execute PostgreSQL {} migration from {}'.format(self.name, filepath))
            if not dry_run:
                self._execute_sql_file(filepath)
        logger.info('PostgreSQL {} schema migration {}'.format(
            self.name,
            'simulated.' if dry_run else 'done.'))

    def _execute_sql_file(self, filepath):
        """Helper method to execute the SQL in a file."""
        with open(filepath) as f:
            schema = f.read()
        # Since called outside request, force commit.
        with self.client.connect(force_commit=True) as conn:
            conn.execute(schema)
