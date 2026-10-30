"""Minimal launcher, bounded feature bootstrap and explicit maintenance invariants."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import startup
import main
import manage
import migration_service as migration
import pet_service
import cloudflare_service as cf
import auth_service


def complete():
    return {t:set(c.split()) for t,c in startup.REQUIRED_COLUMNS.items()}


class StartupTests(unittest.TestCase):
    def test_run_never_migrates_installs_or_configures(self):
        with patch.dict(os.environ,{'HARULOG_CONNECTION':'local'}),patch.object(startup,'ensure_config'),patch.object(startup,'prepare_new_features') as prepare,patch.object(main,'prepare_schema') as schema,patch.object(manage,'install') as install,patch.object(auth_service,'announce_setup'),patch('waitress.serve') as serve:
            startup.run()
            prepare.assert_called_once();serve.assert_called_once()
            schema.assert_not_called();install.assert_not_called()
    def test_missing_config_does_not_prompt_or_create(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(startup,'ROOT',Path(folder)),patch('builtins.input') as prompt:
            with self.assertRaises(RuntimeError):startup.ensure_config()
            prompt.assert_not_called();self.assertEqual(list(Path(folder).iterdir()),[])
    def test_missing_environment_does_not_install(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(startup,'ROOT',Path(folder)),patch.object(manage,'install') as install:
            with self.assertRaises(RuntimeError):startup.require_environment()
            install.assert_not_called();self.assertEqual(list(Path(folder).iterdir()),[])
    def test_existing_config_unchanged(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(startup,'ROOT',Path(folder)),patch.dict(os.environ,{},clear=True):
            path=Path(folder)/'.env';raw=b'DB_NAME=harulog_db\nDB_PASSWORD=preserve\n';path.write_bytes(raw)
            startup.ensure_config();self.assertEqual(path.read_bytes(),raw)
    def test_invalid_connection_mode_rejected(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(startup,'ROOT',Path(folder)),patch.dict(os.environ,{'HARULOG_CONNECTION':'invalid'},clear=True):
            (Path(folder)/'.env').touch()
            with self.assertRaises(RuntimeError):startup.ensure_config()
    def test_missing_cloudflared_fails_before_feature_ddl(self):
        with patch.dict(os.environ,{'HARULOG_CONNECTION':'quick'},clear=True),patch.object(startup,'ensure_config'),patch.object(cf,'find_cloudflared',side_effect=RuntimeError('missing')),patch.object(startup,'prepare_new_features') as prepare:
            with self.assertRaises(RuntimeError):startup.run()
            prepare.assert_not_called()
    def test_launcher_and_document_counts(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual([p.name for p in root.glob('*.bat')],['Run_harulog.bat'])
        self.assertEqual([p.name for p in root.glob('*.md')],['README.md'])
        bat=(root/'Run_harulog.bat').read_text()
        for forbidden in ['pip install','manage.py','init_db','venv .venv']:self.assertNotIn(forbidden,bat)


class FeatureTests(unittest.TestCase):
    def test_pet_record_schema_is_independent_and_owner_scoped(self):
        conn=Mock();pet_service.init_records_schema(conn)
        sql=conn.cursor.return_value.execute.call_args.args[0]
        self.assertIn('CREATE TABLE IF NOT EXISTS pet_records',sql)
        self.assertIn('owner_id BIGINT NOT NULL',sql)
        self.assertIn('FOREIGN KEY (pet_id) REFERENCES pets(id)',sql)

    def test_pet_lineage_schema_and_generation_validation(self):
        conn=Mock();pet_service.init_lineage_schema(conn)
        sql=conn.cursor.return_value.execute.call_args.args[0]
        self.assertIn('CREATE TABLE IF NOT EXISTS pet_lineage',sql)
        self.assertIn('owner_id BIGINT NOT NULL',sql)
        base={'name':'새끼','species':'cat','sex':'female','status':'active','birth_date':'','generation_no':'3','sire_id':'','dam_id':''}
        self.assertEqual(pet_service.validate(base)['generation_no'],3)
        with self.assertRaisesRegex(ValueError,'1부터 50'):
            pet_service.validate({**base,'generation_no':'0'})
        self.assertIn('/api/pets/lineage',{rule.rule for rule in main.app.url_map.iter_rules()})

    def test_pet_screen_uses_minimum_fields_and_admin_badge(self):
        html=(Path(__file__).resolve().parents[1]/'static'/'index.html').read_text()
        for element in ('petName','petSpecies','petSex','petStatus','petBirthDate','petGeneration','petSireId','petDamId','petPhoto','petPedigreeSpecies','petDetailModal','adminBadge'):
            self.assertIn('id="'+element+'"',html)
        for removed in ('petRegistrationNo','petDeathDate','petBreed','petColor','petMicrochipNo','petNotes'):
            self.assertNotIn('id="'+removed+'"',html)

    def test_existing_schema_has_no_writes(self):
        conn=Mock()
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=complete()),patch.object(pet_service,'init_schema') as create:
            startup.prepare_new_features();create.assert_not_called();conn.commit.assert_not_called();conn.close.assert_called_once()
    def test_missing_pets_creates_only_pets(self):
        conn=Mock();before=complete();before.pop('pets')
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',side_effect=[before,complete()]),patch.object(pet_service,'init_schema') as create:
            startup.prepare_new_features();create.assert_called_once_with(conn)
            conn.commit.assert_not_called();conn.close.assert_called_once()
    def test_missing_login_table_is_created_without_credentials(self):
        conn=Mock();before=complete();before.pop('app_members')
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',side_effect=[before,complete()]),patch.object(auth_service,'init_schema') as create,patch.object(pet_service,'init_schema') as pets:
            startup.prepare_new_features();create.assert_called_once_with(conn);pets.assert_not_called()
    def test_existing_invalid_login_table_requires_migration(self):
        conn=Mock();available=complete();available['app_members'].remove('password_hash')
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=available),patch.object(auth_service,'init_schema') as create:
            with self.assertRaisesRegex(RuntimeError,'마이그레이션'):startup.prepare_new_features()
            create.assert_not_called()
    def test_existing_invalid_pets_requires_migration(self):
        conn=Mock();available=complete();available['pets'].remove('species')
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=available),patch.object(pet_service,'init_schema') as create:
            with self.assertRaisesRegex(RuntimeError,'마이그레이션'):startup.prepare_new_features()
            create.assert_not_called()
    def test_missing_core_table_never_creates_feature(self):
        conn=Mock()
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value={}),patch.object(pet_service,'init_schema') as create:
            with self.assertRaises(RuntimeError):startup.prepare_new_features()
            create.assert_not_called()
    def test_create_permission_failure_closes_connection(self):
        conn=Mock();before=complete();before.pop('pets')
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=before),patch.object(pet_service,'init_schema',side_effect=RuntimeError('denied')):
            with self.assertRaisesRegex(RuntimeError,'CREATE 권한'):startup.prepare_new_features()
            conn.close.assert_called_once()
    def test_legacy_cats_notice_without_copy(self):
        conn=Mock();conn.cursor.return_value.fetchone.side_effect=[(2,),(0,)]
        available=complete();available['cats']={'id'}
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=available),patch('builtins.print') as output:
            startup.prepare_new_features()
            self.assertIn('자동 복사하지',str(output.call_args))
            for call in conn.cursor.return_value.execute.call_args_list:self.assertTrue(call.args[0].startswith('SELECT '))
    def test_pet_schema_is_pure_create(self):
        conn=Mock();pet_service.init_schema(conn)
        calls=conn.cursor.return_value.execute.call_args_list
        self.assertEqual(len(calls),1)
        self.assertTrue(calls[0].args[0].startswith('CREATE TABLE IF NOT EXISTS pets'))
    def test_metadata_is_select_only(self):
        conn=Mock();conn.cursor.return_value.fetchall.return_value=[('pets','id')]
        self.assertEqual(startup.schema_columns(conn),{'pets':{'id'}})
        self.assertTrue(conn.cursor.return_value.execute.call_args.args[0].startswith('SELECT '))
        conn.commit.assert_not_called()


class MaintenanceTests(unittest.TestCase):
    def test_install_plan_does_not_create_or_execute(self):
        with patch.object(manage.venv,'EnvBuilder') as builder,patch.object(manage.subprocess,'run') as run:
            manage.install(False);builder.assert_not_called();run.assert_not_called()
    def test_migration_plan_does_not_apply(self):
        with patch.object(startup,'ensure_config'),patch.object(startup,'connect_database',return_value=Mock()),patch.object(migration,'inspect',return_value='plan'),patch.object(migration,'apply') as apply:
            manage.migrate('schema');apply.assert_not_called()
    def test_migration_apply_requires_backup_flag(self):
        with patch.object(startup,'ensure_config'),patch.object(startup,'connect_database',return_value=Mock()),patch.object(migration,'inspect',return_value='plan'),patch.object(migration,'apply') as apply:
            with self.assertRaises(RuntimeError):manage.migrate('schema',True,False)
            apply.assert_not_called()
    def test_explicit_apply_is_single_target(self):
        with patch.object(startup,'ensure_config'),patch.object(startup,'connect_database',return_value=Mock()),patch.object(migration,'inspect',return_value='plan'),patch.object(migration,'apply') as apply:
            manage.migrate('languages',True,True);apply.assert_called_once_with('languages')
    def test_schema_task_never_calls_data_migration(self):
        conn=Mock()
        with patch.object(main,'prepare_schema') as schema,patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=complete()):
            migration.apply('schema');schema.assert_called_once();conn.commit.assert_not_called()
    def test_languages_task_is_transactional(self):
        conn=Mock()
        with patch.object(startup,'connect_database',return_value=conn):migration.apply('languages')
        conn.start_transaction.assert_called_once();conn.commit.assert_called_once()
        for call in conn.cursor.return_value.execute.call_args_list:self.assertTrue(call.args[0].startswith('UPDATE study_videos'))
    def test_cats_task_refuses_nonempty_pets(self):
        conn=Mock();conn.cursor.return_value.fetchone.return_value=(1,)
        available=complete();available['cats']={'id'}
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=available):
            with self.assertRaisesRegex(RuntimeError,'기존 자료'):migration.apply('cats-to-pets')
        conn.commit.assert_not_called();conn.rollback.assert_called_once()
        for call in conn.cursor.return_value.execute.call_args_list:self.assertNotIn('INSERT',call.args[0])
    def test_cats_copy_never_deletes_source(self):
        conn=Mock();conn.cursor.return_value.fetchone.return_value=(0,)
        available=complete();available['cats']={'id'}
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=available):migration.apply('cats-to-pets')
        conn.commit.assert_called_once()
        sql='\n'.join(call.args[0] for call in conn.cursor.return_value.execute.call_args_list)
        self.assertIn('INSERT INTO pets',sql);self.assertIn('UPDATE pets',sql)
        self.assertNotIn('DELETE',sql);self.assertNotIn('DROP',sql)
    def test_failed_copy_rolls_back(self):
        conn=Mock();conn.cursor.return_value.fetchone.return_value=(0,)
        conn.cursor.return_value.execute.side_effect=[None,RuntimeError('failed insert')]
        available=complete();available['cats']={'id'}
        with patch.object(startup,'connect_database',return_value=conn),patch.object(startup,'schema_columns',return_value=available):
            with self.assertRaises(RuntimeError):migration.apply('cats-to-pets')
        conn.commit.assert_not_called();conn.rollback.assert_called_once();conn.close.assert_called_once()


class ShutdownLauncherTests(unittest.TestCase):
    def test_normal_exit_has_no_unconditional_pause(self):
        text=(Path(__file__).resolve().parents[1]/'Run_harulog.bat').read_text()
        tail=text.split('set "HARULOG_EXIT=%errorlevel%"',1)[1]
        self.assertIn('if not "%HARULOG_EXIT%"=="0" (',tail)
        self.assertNotIn('\npause\nexit /b',tail)
        self.assertTrue(tail.rstrip().endswith('exit /b %HARULOG_EXIT%'))


if __name__=='__main__':unittest.main()
