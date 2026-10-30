"""Cloudflare connectivity is independent of program login credentials."""
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cloudflare_service as cf


class CloudflareTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.root=Path(self.folder.name)/'app';self.root.mkdir()
        self.env=patch.dict(os.environ,{},clear=True);self.env.start()
    def tearDown(self):self.env.stop();self.folder.cleanup()
    def test_parent_tools(self):
        p=self.root.parent/'TOOLS'/'cloudflared.exe';p.parent.mkdir();p.touch()
        self.assertEqual(cf.find_cloudflared(self.root),str(p.resolve()))
    def test_configured_path_with_spaces(self):
        p=self.root/'my tools'/'cloudflared.exe';p.parent.mkdir();p.touch()
        os.environ['CLOUDFLARED_PATH']='my tools/cloudflared.exe'
        self.assertEqual(cf.find_cloudflared(self.root),str(p.resolve()))
    def test_missing_explicit_file(self):
        os.environ['CLOUDFLARED_PATH']='missing'
        with self.assertRaises(RuntimeError):cf.find_cloudflared(self.root)
    def test_missing_executable(self):
        with patch.object(cf.shutil,'which',return_value=None),self.assertRaises(RuntimeError):cf.find_cloudflared(self.root)
    def test_fixed_url(self):
        for value in ['', 'http://example.com','https://a:b@example.com','https://example.com/sub']:
            with self.assertRaises(RuntimeError):cf.public_url(value)
        self.assertEqual(cf.public_url('https://example.com/'),'https://example.com')
    def test_tunnel_command_has_no_account_options(self):
        command=cf.tunnel_command('cloudflared',self.root,5000)
        self.assertEqual(command[-1],'http://127.0.0.1:5000')
        self.assertNotIn('password',' '.join(command));self.assertNotIn('username',' '.join(command))
    def test_url_extraction_and_logging(self):
        process=Mock();process.poll.return_value=None;process.stdout=io.StringIO('https://test-url.trycloudflare.com\nconnected\n')
        log=io.StringIO();url,_=cf.wait_for_url(process,log=log);process._harulog_reader.join()
        self.assertEqual(url,'https://test-url.trycloudflare.com');self.assertIn('connected',log.getvalue())
    def test_child_failure(self):
        process=Mock();process.poll.return_value=1;process.stdout=io.StringIO('error')
        with self.assertRaises(RuntimeError):cf.wait_for_url(process)
        process._harulog_reader.join()
    def test_stop_owned_child(self):
        process=Mock();process.poll.return_value=None;cf.stop_process(process);process.terminate.assert_called_once()
    def test_terminate_timeout(self):
        process=Mock();process.poll.return_value=None;process.wait.side_effect=[subprocess.TimeoutExpired('cf',5),0]
        cf.stop_process(process);process.kill.assert_called_once()
    def test_occupied_port_never_opens_tunnel(self):
        from flask import Flask
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));sock.listen()
            with patch.object(cf,'find_cloudflared',return_value='fake'),patch.object(cf.subprocess,'Popen') as child:
                with self.assertRaises(OSError):cf.run(Flask(__name__),self.root,sock.getsockname()[1])
                child.assert_not_called()


if __name__=='__main__':unittest.main()
