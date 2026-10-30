"""New geometric fields declared before any 0.9 validation fitting."""
from . import prepare_quality_data as prepare

VALIDATION_FIELDS=[('w090p10',90.,10.),('w210m20',210.,-20.),('w350p35',350.,35.)]

if __name__=='__main__':
    for spec in VALIDATION_FIELDS:prepare.new_field(spec)
