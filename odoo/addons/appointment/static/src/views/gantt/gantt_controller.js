/* @odoo-module */

import { GanttController } from "@web_gantt/gantt_controller";

export class AppointmentBookingGanttController extends GanttController {

    /**
     * @override
     */
    create(context) {
        super.create({...context, 'booking_gantt_create_record': true})
    }

    /**
     * @override
    */
    get showNoContentHelp() {
        // show if no named row, as it implies both no record and no forced group from resources
        return !this.model.data.rows || (this.model.data.rows.length == 1 && !this.model.data.rows[0].name)
    }
}
