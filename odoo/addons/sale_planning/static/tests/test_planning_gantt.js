/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { getFixture, mount, nextTick, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { PlanningGanttRenderer } from "@planning/views/planning_gantt/planning_gantt_renderer";
import { View } from "@web/views/view";


let serverData;
let target;
QUnit.module('SalePlanning > Views > GanttView', {
    async beforeEach() {
        patchDate(2021, 9, 10, 8, 0, 0);
        setupViewRegistries();
        target = getFixture();
        serverData = {
            models: {
                'planning.slot': {
                    fields: {
                        id: { string: 'ID', type: 'integer' },
                        role_id: { string: 'Role', type: 'many2one', relation: 'planning.role' },
                        sale_line_id: { string: 'Sale Order Item', type: 'many2one', relation: 'sale.order.line' },
                        resource_id: { string: 'Resource', type: 'many2one', relation: 'resource.resource' },
                        start_datetime: { string: 'Start Datetime', type: 'datetime' },
                        end_datetime: { string: 'End Datetime', type: 'datetime' },
                        allocated_percentage: { string: "Allocated percentage", type: "float" },
                    },
                    records: [
                        {
                            id: 1,
                            role_id: 1,
                            sale_line_id: 1,
                            resource_id: false,
                            start_datetime: '2021-10-12 08:00:00',
                            end_datetime: '2021-10-12 12:00:00',
                            allocated_percentage: 0.5,
                        },
                    ],
                },
                'planning.role': {
                    fields: {
                        id: { string: 'ID', type: 'integer' },
                        name: { string: 'Name', type: 'char' },
                    },
                    records: [
                        { 'id': 1, name: 'Developer' },
                        { 'id': 2, name: 'Support Tech' },
                    ],
                },
                'sale.order.line': {
                    fields: {
                        id: { string: 'ID', type: 'integer' },
                        name: { string: 'Product Name', type: 'char' },
                    },
                    records: [
                        { id: 1, name: 'Computer Configuration' },
                    ],
                }
            },
        };
    }
});

QUnit.test('Process domain for plan dialog', async function (assert) {
    let renderer;
    patchWithCleanup(PlanningGanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        }
    });

    const env = await makeTestEnv({
        serverData,
        async mockRPC(_, args) {
            if (args.method === "gantt_resource_work_interval") {
                return  [
                    { false: [["2021-10-12 08:00:00", "2022-10-12 12:00:00"]] },
                ];
            }
        },
    });

    class Parent extends Component {
        setup() {
            this.state = useState({
                arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" default_scale="week"/>`,
                resModel: 'planning.slot',
                type: "gantt",
                domain: [['start_datetime', '!=', false], ['end_datetime', '!=', false]],
                fields: serverData.models['planning.slot'].fields,
            });
        }
    }
    Parent.template = xml`<View t-props="state"/>`;
    Parent.components = { View };

    const parent = await mount(Parent, target, { env });

    let expectedDomain = Domain.and([
        Domain.and([
            new Domain(['&', ...Domain.TRUE.toList({}), ...Domain.TRUE.toList({})]),
            ['|', ['start_datetime', '=', false], ['end_datetime', '=', false]],
        ]),
        [['sale_line_id', '!=', false]],
    ]);
    assert.deepEqual(
        renderer.getPlanDialogDomain(),
        expectedDomain.toList()
    );

    parent.state.domain = ['|', ['role_id', '=', false], '&', ['resource_id', '!=', false], ['start_datetime', '=', false]];
    await nextTick();

    expectedDomain = Domain.and([
        Domain.and([
            new Domain([
                '|', ['role_id', '=', false],
                    '&', ['resource_id', '!=', false], ...Domain.TRUE.toList({}),
            ]),
            ['|', ['start_datetime', '=', false], ['end_datetime', '=', false]],
        ]),
        [['sale_line_id', '!=', false]],
    ]);
    assert.deepEqual(
        renderer.getPlanDialogDomain(),
        expectedDomain.toList()
    );

    parent.state.domain = ['|', ['start_datetime', '=', false], ['end_datetime', '=', false]];
    await nextTick();

    expectedDomain = Domain.and([
        Domain.and([
            Domain.TRUE,
            ['|', ['start_datetime', '=', false], ['end_datetime', '=', false]],
        ]),
        [['sale_line_id', '!=', false]],
    ]);
    assert.deepEqual(
        renderer.getPlanDialogDomain(),
        expectedDomain.toList()
    );
});
