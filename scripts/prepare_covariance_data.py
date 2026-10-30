"""Cache three new geometric validation fields; no centroid fitting here."""
from . import prepare_quality_data as prepare

VALIDATION_FIELDS=[('v060m30',60.,-30.),('v150p45',150.,45.),('v330p10',330.,10.)]


if __name__=='__main__':
    for spec in VALIDATION_FIELDS:prepare.new_field(spec)
