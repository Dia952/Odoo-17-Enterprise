/* @odoo-module */

import { ganttView } from "@web_gantt/gantt_view";
import { registry } from "@web/core/registry";
import { WorkEntriesGanttController } from "./work_entries_gantt_controller";
import { WorkEntriesGanttModel } from "./work_entries_gantt_model";

const viewRegistry = registry.category("views");

export const workEntriesGanttView = {
    ...ganttView,
    Controller: WorkEntriesGanttController,
    Model: WorkEntriesGanttModel,
    buttonTemplate: "hr_work_entry_contract_enterprise.WorkEntriesGanttView.Buttons",
};

viewRegistry.add("work_entries_gantt", workEntriesGanttView);
