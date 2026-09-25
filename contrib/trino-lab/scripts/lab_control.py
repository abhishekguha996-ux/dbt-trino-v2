#!/usr/bin/env python3
"""Review configuration or stop ONLY lab-owned containers. Never global cleanup."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DOCKER = ["docker", "--context", "desktop-linux"]
LABEL = "org.dbt-trino-lab.owner"
PROJECT = "dbt-trino-lab"
COMPOSE = DOCKER + ["compose", "--env-file", "/dev/null", "--project-name", PROJECT,
                    "-f", str(ROOT / "sandbox/compose.yaml"),
                    "--profile", "setup", "--profile", "build", "--profile", "smoke"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(config):
    require(config["name"] == PROJECT, "Unexpected project name")
    require(set(config["services"]) == {"prepare","builder","runner","trino"}, "Unexpected service")
    bounds = {"prepare":(1,1073741824), "builder":(2,4294967296),
              "runner":(0.5,805306368), "trino":(1.5,3221225472)}
    for name, service in config["services"].items():
        for forbidden in ("ports","privileged","cap_add","devices","pid","ipc","secrets",
                          "configs","env_file","environment","extra_hosts","external_links"):
            require(not service.get(forbidden), f"{name}: forbidden setting {forbidden}")
        require(service.get("user") == ("1000:1000" if name == "trino" else "10001:10001"), "Unexpected user")
        require(service.get("read_only") is True, "Writable root filesystem")
        require(service.get("cap_drop") == ["ALL"], "Capabilities are not dropped")
        require(service.get("security_opt") == ["no-new-privileges:true"], "Privilege escalation allowed")
        require(service.get("restart") == "no", "Automatic restart enabled")
        require(service.get("labels",{}).get(LABEL) == PROJECT, "Missing ownership label")
        cpu, memory = bounds[name]
        require(float(service["cpus"]) <= cpu and int(service["mem_limit"]) <= memory, "Resource budget exceeded")
        require(int(service["memswap_limit"]) == int(service["mem_limit"]), "Swap budget changed")
        require(0 < int(service["pids_limit"]) <= (512 if name == "trino" else 256), "Missing PID bound")
        core = service.get("ulimits",{}).get("core")
        # Compose's JSON encoder omits zero-valued soft/hard fields.
        require(isinstance(core,dict) and core.get("soft",0) == 0 and core.get("hard",0) == 0,
                "Core dumps enabled")
        expected_mount = ("trino-data","/data/trino") if name == "trino" else ("work","/workspace")
        mounts = service.get("volumes",[])
        require(len(mounts) == 1, "Unexpected mount count")
        require(mounts[0]["type"] == "volume" and (mounts[0]["source"],mounts[0]["target"]) == expected_mount,
                "Host mount or unexpected volume")
        if name == "builder":
            require(service.get("network_mode") == "none" and not service.get("networks"), "Builder has network access")
        else:
            require(not service.get("network_mode"), "Unexpected network mode")
            require(set(service["networks"]) == ({"acquisition"} if name == "prepare" else {"test"}), "Unexpected network")
        if name in {"trino","runner"}:
            require(service.get("dns") == ["127.0.0.1"], "External DNS enabled")
    network = config["networks"]["test"]
    require(network.get("internal") is True and network.get("enable_ipv6") is False, "Runtime network is not internal")
    require(network.get("driver_opts",{}).get("com.docker.network.bridge.gateway_mode_ipv4") == "isolated",
            "Runtime network exposes a host gateway")
    for name, volume in config["volumes"].items():
        require(name in {"work","trino-data"} and volume.get("name") == f"{PROJECT}_{name}", "Unexpected volume identity")
        require(not volume.get("external") and not volume.get("driver_opts"), "External or bind-backed volume")
        require(volume.get("labels",{}).get(LABEL) == PROJECT, "Unlabelled volume")


def fingerprint():
    paths = [ROOT / ".dockerignore", ROOT / "sources.lock.json"]
    paths += list((ROOT/"sandbox").rglob("*"))
    paths += list((ROOT/"scripts").glob("*.py"))
    paths += [ROOT/"Cargo.lock"]
    paths += list((ROOT/"projects").rglob("*"))
    checksum = hashlib.sha256()
    for path in sorted(paths):
        if path.is_file():
            checksum.update(str(path.relative_to(ROOT)).encode()+b"\0"+path.read_bytes()+b"\0")
    return checksum.hexdigest()


def review():
    config = json.loads(subprocess.check_output(COMPOSE+["config","--format","json"],text=True))
    validate(config)
    report = {"status":"static checks passed; runtime isolation not yet tested",
              "configuration_sha256":fingerprint(),"configuration":config}
    (ROOT/"reports/sandbox-review.json").write_text(json.dumps(report,indent=2)+"\n")
    print(report["status"])
    print("Configuration SHA256: "+report["configuration_sha256"])


def stop():
    ids = subprocess.check_output(DOCKER+["ps","-q","--filter",f"label={LABEL}={PROJECT}"],text=True).split()
    if not ids:
        print("No running lab containers.")
        return
    records = json.loads(subprocess.check_output(DOCKER+["inspect"]+ids,text=True))
    for item in records:
        labels = item["Config"].get("Labels",{})
        require(labels.get(LABEL) == PROJECT and labels.get("com.docker.compose.project") == PROJECT,
                "Container ownership does not match")
        require(labels.get("com.docker.compose.service") in {"prepare","builder","runner","trino"}, "Unknown lab service")
    subprocess.run(DOCKER+["stop","--timeout","30"]+[item["Id"] for item in records],check=True)
    print("Lab containers stopped. Containers and volumes retained.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["review","stop"])
    action = parser.parse_args().command
    review() if action == "review" else stop()
