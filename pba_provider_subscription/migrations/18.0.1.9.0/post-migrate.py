def migrate(cr, version):
    if not version:
        return
    # Convert legacy calendar-hour defaults to business-hour defaults.
    cr.execute(
        """
        UPDATE res_company
           SET pba_sla_hours_low = 80
         WHERE pba_sla_hours_low = 336
        """
    )
    cr.execute(
        """
        UPDATE res_company
           SET pba_sla_hours_normal = 40
         WHERE pba_sla_hours_normal = 168
        """
    )
    cr.execute(
        """
        UPDATE res_company
           SET pba_sla_hours_high = 16
         WHERE pba_sla_hours_high = 48
        """
    )
    cr.execute(
        """
        UPDATE res_company
           SET pba_sla_priority_mismatch_hours = 8
         WHERE pba_sla_priority_mismatch_hours = 24
        """
    )
