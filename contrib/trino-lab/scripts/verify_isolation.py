"""Verify actual lab workloads before executing downloaded code."""
import json
from pathlib import Path
import subprocess
import sys

DOCKER = ['docker', '--context', 'desktop-linux']
OWNER = 'dbt-trino-lab'
BOUNDS = {'builder':(2,4*1024**3), 'runner':(.5,768*1024**2), 'trino':(1.5,3*1024**3)}


def verify(names):
    items = json.loads(subprocess.check_output(DOCKER+['inspect',*names],text=True))
    results = []
    for item in items:
        cfg, host = item['Config'], item['HostConfig']
        labels = cfg['Labels']
        service = labels['com.docker.compose.service']
        assert labels['org.dbt-trino-lab.owner'] == OWNER
        assert labels['com.docker.compose.project'] == OWNER
        assert service in BOUNDS
        assert cfg['User'] == ('1000:1000' if service == 'trino' else '10001:10001')
        assert host['ReadonlyRootfs'] and not host['Privileged']
        assert host['CapDrop'] == ['ALL'] and not host['CapAdd']
        assert 'no-new-privileges:true' in host['SecurityOpt']
        assert not host['PortBindings'] and not host['PublishAllPorts']
        assert not host['Devices'] and host['RestartPolicy']['Name'] == 'no'
        cpus, memory = BOUNDS[service]
        assert 0 < host['NanoCpus'] <= int(cpus*10**9)
        assert 0 < host['Memory'] <= memory and host['MemorySwap'] == host['Memory']
        volumes = [m for m in item['Mounts'] if m['Type'] != 'tmpfs']
        assert len(volumes) == 1
        volume = volumes[0]
        expected = ('trino-data','/data/trino') if service == 'trino' else ('work','/workspace')
        assert volume['Type'] == 'volume' and volume['Name'] == OWNER+'_'+expected[0]
        assert volume['Destination'] == expected[1]
        networks = item['NetworkSettings']['Networks']
        assert set(networks) == ({'none'} if service == 'builder' else {OWNER+'_test'})
        if service != 'builder':
            net = json.loads(subprocess.check_output(DOCKER+['network','inspect',OWNER+'_test'],text=True))[0]
            assert net['Internal'] and not net['EnableIPv6']
            assert net['Options']['com.docker.network.bridge.gateway_mode_ipv4'] == 'isolated'
            assert host['Dns'] == ['127.0.0.1']
        results.append({'name':item['Name'],'service':service,'image_id':item['Image'],
                        'status':'passed','cpu_limit':cpus,'memory_limit':host['Memory'],
                        'network':list(networks),'volume':volume['Name']})
    return results


if __name__ == '__main__':
    result = verify(sys.argv[1:])
    Path('reports/runtime-isolation.json').write_text(json.dumps(result,indent=2)+'\n')
    for record in result:
        Path('reports/isolation-'+record['name'].lstrip('/')+'.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(result,indent=2))
