"""Second Scan integration tests; no changes to prior workflow expectations."""
import csv
import io
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from .models import (Container, Customer, FirstScanSession, ImportBatch, NormalizedLine,
                     ProductMovement, ProductMovesImport, SecondScanMovement, SecondScanSession, SourceFile)


class SecondScanTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('second-operator', password='test')
        self.customer = Customer.objects.create(code='PON', name='PON')
        self.container = Container.objects.create(identifier='SECOND-TEST', customer=self.customer, created_by=self.user)
        source = SourceFile.objects.create(container=self.container, kind='RECEIVED', status='CONFIRMED', original_name='first.xlsx', sha256='a'*64, uploaded_by=self.user)
        self.batch = ImportBatch.objects.create(source_file=source, status='CONFIRMED', created_by=self.user, total_units=2)
        for n in (1, 2):
            NormalizedLine.objects.create(batch=self.batch, source_sheet='First Scan', source_row=n, code='XM0STBFR148', quantity=1, location='T2525')
        self.moves = ProductMovesImport.objects.create(container=self.container, sha256='b'*64, row_count=2, imported_by=self.user)
        for n in (1, 2):
            ProductMovement.objects.create(import_batch=self.moves, source_row=n, product='XM0STBFR148', movement=str(100+n))
        self.client.force_login(self.user)
        self.url = reverse('receiving:second_scan_scanner', args=[self.container.pk])
        self.header = 'Mov_no,Product,Loc,WH_LOC,Serial_no,Long_SKU\r\n'
        self.csv = self.header + '101,XM0STBFR148,T2525,BULK01,,58-26313-454-5-904-262901\r\n102,XM0STBFR148,T2525,BULK01,,58-26313-454-5-904-262901\r\n'

    def upload(self, text=None):
        return self.client.post(self.url, {'action':'import', 'file':SimpleUploadedFile('STOCK_SERIAL_SCANNING.CSV', (text or self.csv).encode())})

    def scan(self, value):
        return self.client.post(self.url, {'action':'scan', 'barcode':value})

    def complete(self, movement='101', serial='SERIAL-A'):
        for value in (movement, 'XM0STBFR148', serial):
            response = self.scan(value)
            self.assertEqual(response.status_code, 200, response.content)
        return response.json()['state']

    def start(self):
        self.assertEqual(self.upload().status_code, 200)
        self.assertEqual(self.scan('AA010').json()['state']['phase'], 'WAITING_MOVEMENT')

    def test_import_scopes_stock_to_container_and_preserves_prior_data(self):
        before = list(self.batch.lines.values())
        old_moves = list(self.moves.rows.values())
        self.upload(self.csv + '999,OTHER,T1111,OTHER,,\r\n')
        self.assertEqual(SecondScanMovement.objects.count(), 2)
        self.assertEqual(list(self.batch.lines.values()), before)
        self.assertEqual(list(self.moves.rows.values()), old_moves)
        session = SecondScanSession.objects.get(container=self.container)
        self.assertEqual(session.source_name, 'STOCK_SERIAL_SCANNING.CSV')
        self.assertEqual(len(session.source_sha256), 64)
        self.assertIsNotNone(session.imported_at)

    def test_continuous_complete_flow_persists_product_validation_and_timestamps(self):
        self.start()
        state = self.complete()
        self.assertEqual((state['scanned'], state['total'], state['phase']), (1, 2, 'WAITING_MOVEMENT'))
        bike = SecondScanMovement.objects.get(movement='101')
        self.assertEqual((bike.location, bike.product_code, bike.serial, bike.wh_loc), ('AA010', 'XM0STBFR148', 'SERIAL-A', 'BULK01'))
        self.assertLessEqual(bike.movement_scanned_at, bike.product_verified_at)
        self.assertLessEqual(bike.product_verified_at, bike.completed_at)
        self.assertEqual(state['recent'][0]['serial'], 'SERIAL-A')
        self.complete('102', 'SERIAL-B')
        self.assertEqual(SecondScanMovement.objects.filter(completed_at__isnull=False).count(), 2)

    def test_serial_cannot_be_saved_before_product_matches(self):
        self.start()
        self.scan('101')
        for value in ('WRONG-BIKE', 'SERIAL-A'):
            response = self.scan(value)
            self.assertEqual(response.status_code, 400)
            self.assertIn('LABEL / BIKE MISMATCH', response.json()['message'])
            self.assertEqual(response.json()['state']['phase'], 'WAITING_PRODUCT')
        bike = SecondScanMovement.objects.get(movement='101')
        self.assertEqual(bike.serial, '')
        self.assertIsNone(bike.completed_at)
        self.assertEqual(SecondScanSession.objects.get().pending_movement_id, bike.pk)
        self.scan('XM0STBFR148')
        self.assertEqual(self.scan('SERIAL-A').status_code, 200)

    def test_unknown_movement_missing_location_and_empty_serial_do_not_count(self):
        self.upload()
        self.assertEqual(self.scan('101').status_code, 400)
        self.scan('AA010')
        self.assertEqual(self.scan('999').status_code, 400)
        self.scan('101'); self.scan('XM0STBFR148')
        self.assertEqual(self.scan('').status_code, 400)
        self.assertEqual(SecondScanMovement.objects.filter(completed_at__isnull=False).count(), 0)

    def test_serial_rejects_product_and_long_code_alias(self):
        self.start(); self.scan('101'); self.scan('XM0STBFR148')
        for serial in ('XM0STBFR148', 'DXM0STBFR148', '58-26313-454-5-904-262901'):
            with self.subTest(serial=serial):
                self.assertEqual(self.scan(serial).status_code, 400)
        self.assertEqual(self.scan('VALID-SERIAL').status_code, 200)

    def test_duplicate_serial_and_completed_movement_are_rejected(self):
        self.start(); self.complete()
        self.assertEqual(self.scan('101').status_code, 400)
        self.scan('102'); self.scan('XM0STBFR148')
        self.assertEqual(self.scan('serial-a').status_code, 400)
        self.assertEqual(self.scan('SERIAL-B').json()['state']['scanned'], 2)

    def test_existing_translogic_serial_including_other_stock_is_rejected(self):
        self.upload(self.csv + '999,OTHER,T1111,OTHER,EXISTING-SERIAL,\r\n')
        self.scan('AA010'); self.scan('101'); self.scan('XM0STBFR148')
        self.assertEqual(self.scan('EXISTING-SERIAL').status_code, 400)
        self.assertEqual(self.scan('NEW-SERIAL').status_code, 200)

    def test_reload_preserves_pending_bike_and_location_change_applies_to_next(self):
        self.start(); self.scan('101'); self.scan('XM0STBFR148'); self.scan('BB020')
        page = self.client.get(self.url)
        self.assertEqual(page.context['scan_state']['phase'], 'WAITING_SERIAL')
        self.assertEqual(page.context['scan_state']['location'], 'BB020')
        self.scan('SERIAL-A')
        self.complete('102', 'SERIAL-B')
        self.assertEqual(SecondScanMovement.objects.get(movement='101').location, 'AA010')
        self.assertEqual(SecondScanMovement.objects.get(movement='102').location, 'BB020')
        self.assertEqual(SecondScanSession.objects.count(), 1)

    def test_finish_and_exact_download_headers_associations_and_download_only(self):
        self.start(); self.complete('102', 'SERIAL-B'); self.complete('101', 'SERIAL-A')
        response = self.client.post(self.url, {'action':'finish'})
        self.assertEqual(response.json()['state']['phase'], 'FINISHED')
        serial = self.client.get(reverse('receiving:second_scan_download', args=[self.container.pk,'serial']))
        loc = self.client.get(reverse('receiving:second_scan_download', args=[self.container.pk,'locations']))
        self.assertEqual(serial['Content-Disposition'], 'attachment; filename="UPSTOCKSERIALSCAN.CSV"')
        self.assertEqual(list(csv.reader(io.StringIO(serial.content.decode()))), [['Mov (10Ch)','Serial','Location'], ['       101','SERIAL-A','AA010'], ['       102','SERIAL-B','AA010']])
        self.assertEqual(list(csv.reader(io.StringIO(loc.content.decode()))), [['code','name'],['AA010','BULK01']])
        self.assertEqual(self.container.generated_exports.count(), 0)
        self.assertEqual(self.scan('103').status_code, 400)
        self.assertNotContains(self.client.get(self.url), 'Copy to Translogic')

    def test_finish_and_download_block_incomplete_bikes(self):
        self.start(); self.scan('101'); self.scan('XM0STBFR148')
        self.assertEqual(self.client.post(self.url, {'action':'finish'}).status_code, 400)
        for kind in ('serial','locations'):
            self.assertEqual(self.client.get(reverse('receiving:second_scan_download', args=[self.container.pk,kind])).status_code, 409)
        self.assertIsNone(SecondScanSession.objects.get().finished_at)

    def test_import_update_is_atomic_preserves_completed_and_blocks_pending(self):
        self.start(); self.complete()
        self.upload(self.csv.replace('BULK01','CHANGED'))
        self.assertEqual(SecondScanMovement.objects.get(movement='101').wh_loc, 'BULK01')
        self.scan('102')
        self.assertContains(self.upload(), 'pending bike')
        self.client.post(self.url, {'action':'cancel'})
        self.assertContains(self.upload(), 'Import / update')
        self.assertEqual(SecondScanMovement.objects.get(movement='101').serial, 'SERIAL-A')

    def test_missing_duplicate_and_product_changed_source_reject_entire_import(self):
        for text in (self.header + '101,XM0STBFR148,T2525,,,,\r\n', self.csv + '101,XM0STBFR148,T2525,BULK01,,\r\n', self.csv.replace('XM0STBFR148','WRONG')):
            self.upload(text)
            self.assertFalse(SecondScanMovement.objects.exists())
            self.assertFalse(SecondScanSession.objects.exists())

    def test_only_pon_and_authenticated_users(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.user)
        self.customer.code = 'OTHER'; self.customer.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_first_scan_active_blocks_import_manual_confirmed_scan_can_import(self):
        session = FirstScanSession.objects.create(container=self.container, batch=self.batch, created_by=self.user)
        self.assertContains(self.upload(), 'Finish First Scan')
        self.assertFalse(SecondScanSession.objects.exists())
        session.status = 'FINISHED'; session.save()
        self.upload()
        self.assertEqual(SecondScanMovement.objects.count(), 2)

    def test_legacy_23_column_csv_positions_match_excel(self):
        output = io.StringIO(); writer = csv.writer(output)
        writer.writerow(['column'+str(n) for n in range(23)])
        for movement in ('101','102'):
            row = ['']*23
            row[0]=movement; row[3]='XM0STBFR148'; row[8]='T2525'; row[18]=''; row[20]='LONG-SKU'; row[21]='WH01'
            writer.writerow(row)
        self.upload(output.getvalue())
        row = SecondScanMovement.objects.get(movement='101')
        self.assertEqual((row.expected_product,row.source_location,row.long_sku,row.wh_loc), ('XM0STBFR148','T2525','LONG-SKU','WH01'))

    def test_database_rejects_serial_without_verified_product(self):
        self.start()
        with self.assertRaises(IntegrityError), transaction.atomic():
            SecondScanMovement.objects.filter(movement='101').update(serial='UNVERIFIED')
        self.assertEqual(SecondScanMovement.objects.get(movement='101').serial, '')

    def test_conflicting_wh_loc_blocks_finish(self):
        self.upload(self.csv.replace('102,XM0STBFR148,T2525,BULK01', '102,XM0STBFR148,T2525,BULK02'))
        self.scan('AA010'); self.complete(); self.complete('102','SERIAL-B')
        result = self.client.post(self.url, {'action':'finish'})
        self.assertEqual(result.status_code, 400)
        self.assertIn('Conflicting WH_LOC', result.json()['message'])

    def test_serial_preserves_scanned_case_and_duplicate_matching_ignores_case(self):
        self.start(); self.complete('101', 'Serial-aB')
        self.assertEqual(SecondScanMovement.objects.get(movement='101').serial, 'Serial-aB')
        self.scan('102'); self.scan('XM0STBFR148')
        self.assertEqual(self.scan('SERIAL-AB').status_code, 400)

    def test_serial_uses_state_without_numeric_format_restrictions(self):
        self.start(); self.scan('101'); self.scan('XM0STBFR148')
        self.assertEqual(self.scan('101').status_code, 200)
        self.assertEqual(SecondScanMovement.objects.get(movement='101').serial, '101')

    def test_excel_serial_export_uses_last_16_and_blocks_suffix_collisions(self):
        self.start(); self.complete('101', 'PREFIX-1234567890123456')
        self.scan('102'); self.scan('XM0STBFR148')
        self.assertEqual(self.scan('OTHER-1234567890123456').status_code, 400)
        self.scan('SERIAL-B'); self.client.post(self.url, {'action':'finish'})
        response = self.client.get(reverse('receiving:second_scan_download', args=[self.container.pk,'serial']))
        self.assertIn('1234567890123456', response.content.decode())
        self.assertNotIn('PREFIX-', response.content.decode())
