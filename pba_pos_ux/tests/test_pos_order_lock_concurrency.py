import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from uuid import uuid4

import psycopg2

from odoo import SUPERUSER_ID, api
from odoo.modules.registry import Registry
from odoo.tests import tagged
from odoo.tests.common import BaseCase, get_db_name
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)

ORDER_COUNT = 120
WORKER_COUNT = 8
RACE_WORKER_COUNT = 8


@tagged(
    "-standard",
    "-at_install",
    "post_install",
    "database_breaking",
    "pba_lock_benchmark",
)
class TestPosOrderLockConcurrency(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = Registry(get_db_name())
        cls.order_prefix = "PBA-CONCURRENCY-%s" % uuid4()
        cls.config_id = False
        cls.session_id = False
        cls.payment_method_id = False
        cls.journal_id = False
        cls.created_payment_method = False
        cls.created_journal = False
        cls.addClassCleanup(cls._cleanup_fixtures)

        with cls.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            cls.classPatch(
                type(env["pos.order"]),
                "_pba_notify_lock_change",
                lambda orders: None,
            )
            company = env.company
            journal = env["account.journal"].create(
                {
                    "name": "PBA Concurrency Cash %s" % cls.order_prefix[-8:],
                    "type": "cash",
                    "code": "P%s" % uuid4().hex[:4].upper(),
                    "company_id": company.id,
                }
            )
            payment_method = env["pos.payment.method"].create(
                {
                    "name": "PBA Concurrency Cash %s" % cls.order_prefix[-8:],
                    "journal_id": journal.id,
                    "company_id": company.id,
                }
            )
            cls.created_journal = True
            cls.created_payment_method = True
            cls.journal_id = journal.id

            config = env["pos.config"].create(
                {
                    "name": "PBA Lock Concurrency",
                    "payment_method_ids": [(6, 0, payment_method.ids)],
                }
            )
            config.open_ui()
            session = config.current_session_id
            session.set_opening_control(0, None)
            orders = env["pos.order"].create(
                [
                    {
                        "company_id": company.id,
                        "session_id": session.id,
                        "amount_tax": 0.0,
                        "amount_total": 10.0,
                        "amount_paid": 0.0,
                        "amount_return": 0.0,
                        "uuid": "%s-%03d" % (cls.order_prefix, index),
                        "pos_reference": "Order %s-%03d"
                        % (cls.order_prefix, index),
                    }
                    for index in range(ORDER_COUNT)
                ]
            )
            cls.config_id = config.id
            cls.session_id = session.id
            cls.payment_method_id = payment_method.id
            cls.order_ids = orders.ids
        cls.worker_envs = [
            api.Environment(cls.registry.cursor(), SUPERUSER_ID, {})
            for _index in range(max(WORKER_COUNT, RACE_WORKER_COUNT))
        ]

    @classmethod
    def _cleanup_fixtures(cls):
        for env in getattr(cls, "worker_envs", []):
            env.cr.close()
        with cls.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            orders = env["pos.order"].search(
                [("uuid", "=like", "%s-%%" % cls.order_prefix)]
            )
            orders.unlink()
            env["pos.session"].browse(cls.session_id).exists().unlink()
            env["pos.config"].browse(cls.config_id).exists().unlink()
            if cls.created_payment_method:
                env["pos.payment.method"].browse(
                    cls.payment_method_id
                ).exists().unlink()
            if cls.created_journal:
                env["account.journal"].browse(cls.journal_id).exists().unlink()

    def _reset_locks(self, order_ids):
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            orders = env["pos.order"].browse(order_ids).exists()
            orders.write(orders._pba_lock_clear_vals())

    def _acquire_orders(self, order_ids, worker_index, barrier):
        barrier.wait(timeout=20)
        env = self.worker_envs[worker_index]
        env.clear()
        started_at = perf_counter()
        results = []
        for order_id in order_ids:
            result = env["pos.order"].pba_acquire_order_lock(
                order_id,
                "owner-device-%02d" % worker_index,
                "Employee %02d" % worker_index,
                SUPERUSER_ID,
                1000 + worker_index,
            )
            results.append(result["success"])
        env.cr.commit()
        return results, perf_counter() - started_at

    def _intrude_orders(self, order_ids, worker_index, barrier):
        barrier.wait(timeout=20)
        env = self.worker_envs[worker_index]
        env.clear()
        started_at = perf_counter()
        results = []
        for order_id in order_ids:
            result = env["pos.order"].pba_acquire_order_lock(
                order_id,
                "intruder-device-%02d" % worker_index,
                "Intruder %02d" % worker_index,
                SUPERUSER_ID,
                2000 + worker_index,
            )
            results.append(result["success"])
        env.cr.commit()
        return results, perf_counter() - started_at

    def _release_orders(self, order_ids, worker_index, barrier):
        barrier.wait(timeout=20)
        env = self.worker_envs[worker_index]
        env.clear()
        started_at = perf_counter()
        results = []
        for order_id in order_ids:
            result = env["pos.order"].pba_release_order_lock(
                order_id,
                "owner-device-%02d" % worker_index,
            )
            results.append(result["success"])
        env.cr.commit()
        return results, perf_counter() - started_at

    def _run_workers(self, callback, partitions):
        barrier = threading.Barrier(len(partitions))
        started_at = perf_counter()
        with ThreadPoolExecutor(max_workers=len(partitions)) as executor:
            futures = [
                executor.submit(callback, order_ids, index, barrier)
                for index, order_ids in enumerate(partitions)
            ]
            results = [future.result(timeout=120) for future in futures]
        return results, perf_counter() - started_at

    @mute_logger("odoo.sql_db")
    def test_parallel_employees_contend_for_one_order(self):
        order_id = self.order_ids[0]
        self._reset_locks([order_id])
        barrier = threading.Barrier(RACE_WORKER_COUNT)

        def acquire(worker_index):
            barrier.wait(timeout=20)
            env = self.worker_envs[worker_index]
            env.clear()
            env.cr.execute("SET LOCAL lock_timeout = '5s'")
            try:
                result = env["pos.order"].pba_acquire_order_lock(
                    order_id,
                    "race-device-%02d" % worker_index,
                    "Race Employee %02d" % worker_index,
                    SUPERUSER_ID,
                    3000 + worker_index,
                )
                env.cr.commit()
                return result
            except (
                psycopg2.errors.LockNotAvailable,
                psycopg2.errors.SerializationFailure,
            ):
                env.cr.rollback()
                return {
                    "success": False,
                    "reason": "locked",
                    "owner_name": False,
                }

        started_at = perf_counter()
        with ThreadPoolExecutor(max_workers=RACE_WORKER_COUNT) as executor:
            results = list(executor.map(acquire, range(RACE_WORKER_COUNT)))
        elapsed = perf_counter() - started_at
        winners = [result for result in results if result["success"]]

        self.assertEqual(len(winners), 1)
        self.assertEqual(
            sum(result["reason"] == "locked" for result in results),
            RACE_WORKER_COUNT - 1,
        )
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            order = env["pos.order"].browse(order_id)
            self.assertEqual(order.pba_lock_owner_name, winners[0]["owner_name"])
            self.assertEqual(order.session_id.id, self.session_id)
        _logger.info(
            "PBA lock race benchmark: %d contenders in %.4fs",
            RACE_WORKER_COUNT,
            elapsed,
        )

    def test_parallel_order_stress_keeps_orders_and_owners(self):
        self._reset_locks(self.order_ids)
        partitions = [
            self.order_ids[index::WORKER_COUNT] for index in range(WORKER_COUNT)
        ]

        acquire_results, acquire_elapsed = self._run_workers(
            self._acquire_orders,
            partitions,
        )
        self.assertTrue(all(all(result[0]) for result in acquire_results))

        intrude_results, intrude_elapsed = self._run_workers(
            self._intrude_orders,
            partitions,
        )
        self.assertFalse(any(any(result[0]) for result in intrude_results))

        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            orders = env["pos.order"].browse(self.order_ids).exists()
            self.assertEqual(len(orders), ORDER_COUNT)
            self.assertEqual(set(orders.mapped("session_id").ids), {self.session_id})
            for worker_index, order_ids in enumerate(partitions):
                worker_orders = orders.filtered(lambda order: order.id in order_ids)
                self.assertEqual(
                    set(worker_orders.mapped("pba_lock_device_token")),
                    {"owner-device-%02d" % worker_index},
                )
                self.assertEqual(
                    set(worker_orders.mapped("pba_lock_owner_name")),
                    {"Employee %02d" % worker_index},
                )
                self.assertEqual(
                    set(worker_orders.mapped("pba_lock_owner_employee_id")),
                    {1000 + worker_index},
                )

        release_results, release_elapsed = self._run_workers(
            self._release_orders,
            partitions,
        )
        self.assertTrue(all(all(result[0]) for result in release_results))

        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            orders = env["pos.order"].browse(self.order_ids).exists()
            self.assertEqual(len(orders), ORDER_COUNT)
            self.assertTrue(
                all(not token for token in orders.mapped("pba_lock_device_token"))
            )
            self.assertTrue(
                all(not name for name in orders.mapped("pba_lock_owner_name"))
            )
            self.assertTrue(
                all(
                    not employee_id
                    for employee_id in orders.mapped("pba_lock_owner_employee_id")
                )
            )

        _logger.info(
            "PBA lock stress benchmark: %d orders, %d workers, "
            "acquire %.2f ops/s, reject %.2f ops/s, release %.2f ops/s",
            ORDER_COUNT,
            WORKER_COUNT,
            ORDER_COUNT / acquire_elapsed,
            ORDER_COUNT / intrude_elapsed,
            ORDER_COUNT / release_elapsed,
        )
