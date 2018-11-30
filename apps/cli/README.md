# DIANA CLI

Derek Merck

## DICOM Analytics and Archive (DIANA)

1. `diana` -- Pythonic API for DICOM-related systems and data types
2. `diana-cli` -- CLI wrapper for invoking tasks and daemons
3. `diana-stack` -- Docker swarm definitions for DICOM-service stacks
4. `diana-embedded` -- Balena compose definitions and images for embedded DICOM services
5. `trialist` -- A Flack front end for a diana-stack supporting multiple image registries
5. `radcatr` -- TCL UI for RADCAT report review


## The DIANA Command Line

### Proxied Pull by Accession Number

Batch:

$ `DIANA pull --accession_number 12345 --anonymize my_orthanc pacs`

Batch:

$ `DIANA pull --file accesions.txt --anonymize my_orthanc pacs`


### Mock Scanner Daemon

$ `DIANA mock --rate 10 my_orthanc`

