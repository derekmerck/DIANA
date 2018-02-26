"""
Script used to generate large amounts of consistent sample enrollment data
"""

from hashlib import md5
from datetime import datetime, timedelta
import logging
from pprint import pformat
import random
import csv
from GUIDMint import GUIDMint

def gen_patient(seed, mint):

    def get_sex():
        return random.choice(["M", "F"])

    def get_exam_id():
        return md5(seed.__str__().encode('utf-8')).hexdigest()[0:16]

    def get_inst():
        return random.choices(institutions, weights=inst_weights)[0]

    def get_exam_date():
        offset = random.randrange(-60,-10)
        return datetime.today()+timedelta(days=offset)

    def get_trials():
        return random.choices(trials, weights=trial_weights)[0]

    def get_enrollment():
        if trial:
            return random.choice([True, False])
        else:
            return None

    def get_enrollment_date():
        if enrolled:
            offset = random.randrange(1,10)
            return exam_date + timedelta(days=offset)
        else:
            return None

    random.seed(seed)

    sex = get_sex()
    age = random.randint(19,65)

    exam_date = get_exam_date()
    trial = get_trials()
    enrolled = get_enrollment()
    enrollment_date = get_enrollment_date()
    if enrollment_date:
        enrollment_date_str = enrollment_date.isoformat()
    else:
        enrollment_date_str = None

    guid, name, dob = mint.pseudo_identity(str(seed), gender=sex, age=age)

    p = {'name': name,
         'sex': sex,
         'dob': dob,
         'institution': get_inst(),
         'mrn': guid,
         'exam_id': get_exam_id(),
         'exam_date': exam_date.isoformat(),
         'eligible': trial,
         'enrolled': get_enrollment(),
         'enrollment_date': enrollment_date_str
         }

    return p


def csv_dict_writer(path, data):
    """
    Writes a CSV file using DictWriter
    """
    fieldnames = list(data[0].keys())
    logging.debug(fieldnames)

    with open(path, "w") as out_file:
        writer = csv.DictWriter(out_file, delimiter=',', fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


trials = [None, "efFECT", "insPECT", "eLECT", "corRECT", "anticiPATE", "amelioRATE"]
trial_weights = [30, 10, 10, 5, 2, 15, 5]
institutions = ["Northern Hospital", "Southern Hospital", "Eastern Medical Center", "Western Clinic"]
inst_weights = [15,10,5,2]

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    mint = GUIDMint()

    pp = []
    for seed in range(1,10):
        p = gen_patient(seed, mint)
        logging.debug(pformat(p))
        pp.append(p)

    # csv_dict_writer("my_patients.csv", pp)

