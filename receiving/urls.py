from django.urls import path

from . import views, second_scan


app_name = "receiving"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("catalog/upload/", views.upload_product_catalog, name="upload_product_catalog"),
    path("catalog/sync/", views.sync_product_catalog, name="sync_product_catalog"),
    path("containers/<int:pk>/", views.container_detail, name="container_detail"),
    path("containers/<int:pk>/first-scan/", views.first_scan_scanner, name="first_scan_scanner"),
    path("containers/<int:pk>/second-scan/", second_scan.scanner, name="second_scan_scanner"),
    path("containers/<int:pk>/second-scan/download/<str:kind>/", second_scan.download, name="second_scan_download"),
    path("containers/<int:pk>/edit/", views.edit_container, name="edit_container"),
    path("containers/<int:pk>/upload/", views.upload_source, name="upload_source"),
    path("containers/<int:pk>/import-server/", views.import_server_source, name="import_server_source"),
    path("containers/<int:pk>/comparison/", views.comparison, name="comparison"),
    path("containers/<int:pk>/product-check/", views.product_check, name="product_check"),
    path("containers/<int:pk>/product-check/export/", views.export_product_check, name="export_product_check"),
    path("containers/<int:pk>/new-product-import/export/", views.export_new_products, name="export_new_products"),
    path("containers/<int:pk>/stage2/", views.stage2, name="stage2"),
    path("containers/<int:pk>/stage2/sync-product-moves/", views.sync_product_moves, name="sync_product_moves"),
    path("containers/<int:pk>/stage2/upload-product-moves/", views.upload_product_moves, name="upload_product_moves"),
    path("containers/<int:pk>/stage2/download-upstockserial/", views.download_current_upstockserial, name="download_current_upstockserial"),
    path("containers/<int:pk>/stage2/copy-upstockserial/", views.transfer_upstockserial, name="transfer_upstockserial"),
    path("containers/<int:pk>/new-product-import/copy-to-translogic/", views.transfer_new_product_import, name="transfer_new_product_import"),
    path("containers/<int:pk>/stage2/generate-upstockserial/", views.generate_upstockserial, name="generate_upstockserial"),
    path("stage2/exports/<int:export_id>/download/", views.download_upstockserial, name="download_upstockserial"),
    path("containers/<int:pk>/client-report/download/", views.download_current_client_report, name="download_current_client_report"),
    path("containers/<int:pk>/client-report/generate/", views.generate_client_report, name="generate_client_report"),
    path("containers/<int:pk>/complete/", views.mark_container_complete, name="mark_container_complete"),
    path("containers/<int:pk>/reopen/", views.reopen_container, name="reopen_container"),
    path("client-report/exports/<int:export_id>/download/", views.download_client_report, name="download_client_report"),
    path("sources/<int:source_id>/configure/", views.configure_import, name="configure_import"),
    path("sources/<int:source_id>/source-preview/", views.source_file_preview, name="source_file_preview"),
    path("imports/<int:batch_id>/preview/", views.batch_preview, name="batch_preview"),
    path("imports/<int:batch_id>/confirm/", views.confirm_batch, name="confirm_batch"),
]
