from app.services.compliance.rules.product_name import register_product_name_rules
from app.services.compliance.rules.mrp import register_mrp_rules
from app.services.compliance.rules.net_quantity import register_net_quantity_rules
from app.services.compliance.rules.manufacturer import register_manufacturer_rules
from app.services.compliance.rules.packer import register_packer_rules
from app.services.compliance.rules.importer import register_importer_rules
from app.services.compliance.rules.dates import register_date_rules
from app.services.compliance.rules.consumer_care import register_consumer_care_rules
from app.services.compliance.rules.country_of_origin import register_country_of_origin_rules

def init_default_rules():
    """Initializes and registers all modular statutory rules in the centralized registry."""
    register_product_name_rules()
    register_mrp_rules()
    register_net_quantity_rules()
    register_manufacturer_rules()
    register_packer_rules()
    register_importer_rules()
    register_date_rules()
    register_consumer_care_rules()
    register_country_of_origin_rules()
