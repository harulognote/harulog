"""Explicit maintenance entry point. Never imported or invoked by Run_harulog.bat."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parent


def install(apply=False):
    print('수동 설치 작업: .venv가 없으면 생성하고 requirements.txt의 패키지를 설치합니다. DB/설정/자료는 변경하지 않습니다.')
    if not apply:
        print('실행하려면: py -3 manage.py install --apply')
        return
    if sys.version_info<(3,10):raise RuntimeError('Python 3.10 이상이 필요합니다.')
    target=ROOT/'.venv'
    python=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not target.exists():venv.EnvBuilder(with_pip=True).create(target)
    if not python.is_file():raise RuntimeError('기존 .venv가 손상되었거나 이 OS와 다릅니다. 자동 삭제하지 않습니다.')
    subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements.txt')],check=True)
    print('[OK] 수동으로 요청한 패키지 설치 완료. DB와 .env는 변경하지 않았습니다.')


def link_ai():
    from dotenv import dotenv_values
    value=input('기존 AI 설정 .env 파일 경로 (키 자체를 입력하지 마세요): ').strip().strip('"')
    if not value:return
    path=Path(value).expanduser()
    if path.is_dir():path=path/'.env'
    if not path.is_file():raise RuntimeError('설정 파일을 찾을 수 없습니다.')
    values=dotenv_values(path,interpolate=False,encoding='utf-8-sig')
    if not str(values.get('OPENAI_API_KEY') or '').strip():raise RuntimeError('해당 파일에 AI 설정이 없습니다.')
    (ROOT/'harulog_ai_link.json').write_text(json.dumps({'env_file':str(path.resolve())},ensure_ascii=False,indent=2),encoding='utf-8')
    print('[OK] 설정 파일의 경로만 연결했습니다. 키를 복사하거나 출력하지 않았습니다.')


def migrate(target,apply=False,backup_confirmed=False,owner_id=None):
    import startup
    import migration_service
    startup.ensure_config()
    print('[ownership] 사용자별 자료 분리' if target=='ownership' else migration_service.description(target))
    conn=startup.connect_database()
    try:
        print(migration_service.inspect_ownership(conn,owner_id) if target=='ownership' else migration_service.inspect(conn,target))
    finally:conn.close()
    if not apply:
        print('위 내용은 조회 결과입니다. 변경하지 않았습니다. README.md의 별도 적용 절차를 확인해 주세요.')
        return
    if not backup_confirmed:
        raise RuntimeError('DB 백업과 서버 중단 후 --backup-confirmed를 명시해야 합니다. 변경하지 않았습니다.')
    if target=='ownership':migration_service.apply_ownership(owner_id)
    else:migration_service.apply(target)


def main():
    parser=argparse.ArgumentParser(description='HaruLog 수동 관리. 일반 실행에서는 호출하지 않습니다.')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('install');p.add_argument('--apply',action='store_true')
    sub.add_parser('link-ai')
    p=sub.add_parser('migrate')
    p.add_argument('target',choices=['schema','languages','cats-to-pets','ownership'])
    p.add_argument('--apply',action='store_true');p.add_argument('--backup-confirmed',action='store_true')
    p.add_argument('--owner-id',type=int)
    args=parser.parse_args()
    try:
        os.chdir(ROOT)
        if args.command=='install':
            install(args.apply);return 0
        import startup
        python=startup.require_environment()
        if os.path.normcase(os.path.abspath(sys.executable))!=os.path.normcase(os.path.abspath(python)):
            return subprocess.call([str(python),str(ROOT/'manage.py'),*sys.argv[1:]])
        if args.command=='migrate':migrate(args.target,args.apply,args.backup_confirmed,args.owner_id)
        else:
            startup.ensure_config()
            if args.command=='link-ai':link_ai()
        return 0
    except KeyboardInterrupt:return 0
    except Exception as error:
        print('[ERROR] '+str(error),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
