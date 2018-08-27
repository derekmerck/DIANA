import os, logging, yaml

def dev():
    os.environ['DIANA_BROKER']="redis://:passw0rd!@192.168.33.10:6379/1"
    os.environ['DIANA_RESULT']="redis://:passw0rd!@192.168.33.10:6379/2"
    service_cfg = "test/dev_services.yml"
    return service_cfg

def prod():
    os.environ['DIANA_BROKER']="redis://:D1anA!@rad_research:6379/1"
    os.environ['DIANA_RESULT']="redis://:D1anA!@rad_research:6379/2"
    service_cfg = "_secrets/lifespan_services.yml"
    return service_cfg

def set_services():

    logging.basicConfig(level=logging_level)
    service_cfg = service_func()

    with open(service_cfg, "r") as f:
        services = yaml.safe_load(f)

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return services



# --------------------------
# Set modes here
# --------------------------

logging_level = logging.DEBUG
service_func = prod
test_star = True

services = set_services()


