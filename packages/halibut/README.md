# Halibut :fish:

Ian Pan <ian_pan@brown.edu>  
Spring 2018

Run a Keras classifier on a DICOM image.


## Dependencies

- Keras
- Scipy
- Cython


## Usage

```bash
$ python apps/cli/clf_chest_pose.py -w tests/resources/chest_cr/chest_pose_weights.h5  tests/resources/chest_cr/CR00.dcm
>>PREDICTED VIEW: LATERAL (1.0)<<

$ python apps/cli/clf_chest_pose.py -w tests/resources/chest_cr/chest_pose_weights.h5  tests/resources/chest_cr/CR01.dcm
>>PREDICTED VIEW: FRONTAL (1.0)<<

```

## Notes

Originally "Hemorrhagic Lesion Identification for Brain Trauma".


## License

MIT