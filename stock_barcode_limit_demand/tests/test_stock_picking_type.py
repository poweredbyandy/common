from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockBarcodeLimitDemand(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picking_type = cls.env.ref("stock.picking_type_in")

    def test_barcode_config_includes_block_over_demand(self):
        self.picking_type.barcode_block_over_demand = True
        config = self.picking_type._get_barcode_config()
        self.assertTrue(config["barcode_block_over_demand"])

    def test_barcode_config_can_disable_block_over_demand(self):
        self.picking_type.barcode_block_over_demand = False
        config = self.picking_type._get_barcode_config()
        self.assertFalse(config["barcode_block_over_demand"])
