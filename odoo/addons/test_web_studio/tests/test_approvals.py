from odoo import Command

from odoo.tests.common import TransactionCase, tagged

@tagged("-at_install", "post_install")
class TestStudioApprovals(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = cls.env.ref("base.user_admin")
        cls.demo_user = cls.env["res.users"].search([("login", "=", "demo")], limit=1)
        if not cls.demo_user:
            cls.demo_user = cls.env["res.users"].create({
                "login": "demo",
                "name": "demo",
                "email": "demo@demo",
                "groups_id": [Command.link(cls.env.ref("base.group_user").id)]
            })

        cls.other_user = cls.env["res.users"].create({
            "name": "test",
            "login": "test",
            "email": "test@test.test",
            "groups_id": [Command.link(cls.env.ref("base.group_user").id)]
        })

        cls.test_user_2 = cls.env["res.users"].create({
            "name": "test_2",
            "login": "test_2",
            "email": "test_2@test_2.test_2",
            "groups_id": [Command.link(cls.env.ref("base.group_user").id)]
        })

    def test_approval_method_two_models(self):
        IrModel = self.env["ir.model"]

        self.env["studio.approval.rule"].create([
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            },
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_confirm",
                "notification_order": "2",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(self.other_user.id)],
                "exclusive_user": True,
            },
            {
                "model_id": IrModel._get("test.studio.model_action2").id,
                "method": "action_confirm",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
                "exclusive_user": True,
            }
        ])

        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })

        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()

        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.admin_user.name} An approval for 'False' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 1)

        with self.with_user("admin"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()

        self.assertFalse(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, "@test An approval for 'False' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 1)

        with self.with_user("test"):
            self.env["test.studio.model_action"].browse(model_action.id).action_confirm()

        self.assertTrue(model_action.confirmed)
        self.assertEqual(model_action.message_ids[0].preview, "Approved as User types / Internal User")
        self.assertEqual(len(model_action.activity_ids), 0)

    def test_notify_higher_notification_order(self):
        IrModel = self.env["ir.model"]

        self.env["studio.approval.rule"].create([
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "domain": "[('step', '<', 1)]",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
            },
            {
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "domain": "[('step', '>=', 1)]",
                "notification_order": "2",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(self.other_user.id)],
            },
            {
                "model_id": IrModel._get("test.studio.model_action2").id,
                "method": "action_step",
                "notification_order": "1",
                "responsible_id": self.admin_user.id,
                "users_to_notify": [Command.link(2)],
            },
        ])

        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })
        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 1)
        self.assertEqual(model_action.message_ids[0].preview, "@test An approval for 'False' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 1)

    def test_entries_approved_by_other_read_by_regular_user(self):
        IrModel = self.env["ir.model"]
        self.env["studio.approval.rule"].create([
            {   # rule 0
                "name": "R0",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "1",
                "exclusive_user": True,
                "responsible_id": self.admin_user.id,
            },
            {
                "name": "R1",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "exclusive_user": True,
                "responsible_id": self.admin_user.id,
            },
            {
                "name": "R2",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "2",
                "exclusive_user": True,
                "responsible_id": self.admin_user.id,
            },
            {
                "name": "R3",
                "model_id": IrModel._get("test.studio.model_action").id,
                "method": "action_step",
                "notification_order": "3",
                "exclusive_user": True,
                "responsible_id": self.test_user_2.id,
            },
        ])
        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })
        with self.with_user("admin"):
            # validates rule 0
            # this will create an entry belonging to admin
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[:2].mapped("preview"), ["An approval for 'R2' has been requested on test", "An approval for 'R1' has been requested on test"])
        self.assertEqual(len(model_action.activity_ids), 2)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.admin_user.ids)

        with self.with_user("test"):
            # validates rule 1
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "Approved as User types / Internal User")
        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.admin_user.ids)

        with self.with_user("demo"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, "An approval for 'R3' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 1)
        self.assertEqual(model_action.activity_ids.mapped("user_id").ids, self.test_user_2.ids)

        with self.with_user("test_2"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()

        self.assertEqual(model_action.step, 1)
        self.assertEqual(model_action.message_ids[0].preview, "Approved as User types / Internal User")
        self.assertEqual(len(model_action.activity_ids), 0)

    def test_no_responsible_but_user_notified(self):
        IrModel = self.env["ir.model"]
        self.env["studio.approval.rule"].create([
            {
                "name": "R0",
                "model_id": IrModel._get("test.studio.model_action").id,
                "group_id": self.env.ref("base.group_system").id,
                "method": "action_step",
                "notification_order": "1",
                "users_to_notify": [Command.link(self.demo_user.id), Command.link(self.other_user.id)]
            }
        ])
        model_action = self.env["test.studio.model_action"].create({
            "name": "test"
        })
        with self.with_user("test_2"):
            self.env["test.studio.model_action"].browse(model_action.id).action_step()
        self.assertEqual(model_action.step, 0)
        self.assertEqual(model_action.message_ids[0].preview, f"@{self.demo_user.name} @test An approval for 'R0' has been requested on test")
        self.assertEqual(len(model_action.activity_ids), 0)
