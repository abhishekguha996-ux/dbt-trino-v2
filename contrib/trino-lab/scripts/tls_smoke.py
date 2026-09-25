"""Local TLS and password transport tests through the candidate dbt binary.

The TLS endpoint lives on loopback in the Linux runner. It forwards only to the
lab Trino service and checks a synthetic password. This is not an LDAP server test.
"""
import base64
from contextlib import closing
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import threading
from urllib.parse import quote

ROOT=Path('/workspace')
BINARY=ROOT/'source/dbt-841c74e863df51b89d208b1ad0eca388aa0f32a4/target/debug/dbt'
LAB=ROOT/'tls-lab'
PASSWORD='synthetic:p@ss&word'
AUTH='Basic '+base64.b64encode(('dbt_lab:'+PASSWORD).encode()).decode()


def command(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=60)


def rewrite(value):
    if isinstance(value,dict):
        return {key:rewrite(item) for key,item in value.items()}
    if isinstance(value,list):
        return [rewrite(item) for item in value]
    if isinstance(value,str) and value.startswith('http://trino:8080/'):
        return 'https://localhost:8443/'+value[len('http://trino:8080/'):]
    return value


class Proxy(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass

    def forward(self):
        if self.headers.get('Authorization') != AUTH:
            self.send_response(401)
            self.send_header('WWW-Authenticate','Basic realm="synthetic-lab"')
            self.end_headers()
            self.wfile.write(b'Invalid lab credentials')
            return
        if not self.path.startswith('/v1/'):
            self.send_error(404)
            return
        length=int(self.headers.get('Content-Length','0'))
        if length > 1024*1024:
            self.send_error(413)
            return
        body=self.rfile.read(length) if length else None
        headers={key:value for key,value in self.headers.items()
                 if key.lower().startswith('x-trino-') or key.lower()=='content-type'}
        with closing(http.client.HTTPConnection('trino',8080,timeout=30)) as upstream:
            upstream.request(self.command,self.path,body,headers)
            response=upstream.getresponse()
            data=response.read()
            if response.getheader('Content-Type','').startswith('application/json'):
                data=json.dumps(rewrite(json.loads(data))).encode()
            self.send_response(response.status)
            for key,value in response.getheaders():
                if key.lower() not in {'content-length','transfer-encoding','connection','content-encoding'}:
                    self.send_header(key,value)
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    do_GET=forward
    do_POST=forward
    do_DELETE=forward


def main():
    LAB.mkdir(mode=0o700,exist_ok=True)
    if not (LAB/'server.crt').exists():
        command(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','2',
                 '-subj','/CN=dbt Trino disposable lab CA','-keyout',str(LAB/'ca.key'),'-out',str(LAB/'ca.crt')])
        command(['openssl','req','-new','-newkey','rsa:2048','-nodes','-subj','/CN=localhost',
                 '-keyout',str(LAB/'server.key'),'-out',str(LAB/'server.csr')])
        (LAB/'extensions.cnf').write_text('subjectAltName=DNS:localhost\nbasicConstraints=critical,CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n')
        command(['openssl','x509','-req','-in',str(LAB/'server.csr'),'-CA',str(LAB/'ca.crt'),
                 '-CAkey',str(LAB/'ca.key'),'-CAcreateserial','-days','2','-extfile',str(LAB/'extensions.cnf'),
                 '-out',str(LAB/'server.crt')])
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(LAB/'server.crt',LAB/'server.key')
    server=ThreadingHTTPServer(('127.0.0.1',8443),Proxy)
    server.socket=context.wrap_socket(server.socket,server_side=True)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    project=LAB/'project';project.mkdir(exist_ok=True)
    (project/'dbt_project.yml').write_text("name: tls_lab\nversion: '1.0'\nconfig-version: 2\nprofile: tls_lab\n")
    reports=[]
    try:
        for name,host,password,trusted,expected in [
            ('trusted_tls_password','localhost',PASSWORD,True,True),
            ('incorrect_password','localhost','incorrect',True,False),
            ('untrusted_certificate','localhost',PASSWORD,False,False),
            ('hostname_mismatch','127.0.0.1',PASSWORD,True,False),
        ]:
            profile={'tls_lab':{'target':'lab','outputs':{'lab':{
                'type':'trino','host':host,'port':8443,'user':'dbt_lab',
                'database':'memory','schema':'default','threads':1,'method':'ldap',
                'password':password,'http_scheme':'https'}}}}
            (project/'profiles.yml').write_text(json.dumps(profile))
            env=os.environ.copy()
            env.update(DBT_ALLOW_EXPERIMENTAL_ADAPTERS='yes',LD_LIBRARY_PATH='/workspace/driver',
                       DBT_SEND_ANONYMOUS_USAGE_STATS='false')
            if trusted:
                env['SSL_CERT_FILE']=str(LAB/'ca.crt')
            else:
                env.pop('SSL_CERT_FILE',None)
            result=subprocess.run([str(BINARY),'debug','--debug','--project-dir',str(project),'--profiles-dir',str(project)],
                                  env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
            text=result.stdout
            assert PASSWORD not in text and quote(PASSWORD,safe='') not in text, 'Synthetic password leaked in dbt output'
            for log_path in (project/'logs').glob('*.log'):
                log_text=log_path.read_text(errors='replace')
                assert PASSWORD not in log_text and quote(PASSWORD,safe='') not in log_text, 'Synthetic password leaked in a dbt log'
            (ROOT/'reports'/f'tls-{name}.log').write_text(text)
            assert (result.returncode == 0) == expected, f'{name}: unexpected exit {result.returncode}; see report'
            if not expected:
                markers={'incorrect_password':['401','unauthorized','credentials'],
                         'untrusted_certificate':['certificate','unknown authority'],
                         'hostname_mismatch':['certificate','127.0.0.1']}
                assert any(marker in text.lower() for marker in markers[name]), f'{name}: failed for another reason'
            reports.append({'name':name,'status':'pass','dbt_returncode':result.returncode})
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5)
        (ROOT/'reports/tls-tests.json').write_text(json.dumps(reports,indent=2)+'\n')
        # Passwords and keys remain only in the private disposable volume.
    print(json.dumps(reports,indent=2))

if __name__ == '__main__':
    main()
