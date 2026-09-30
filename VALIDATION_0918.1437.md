# VALIDATION 0918.1437

## Scope
Home screen / container selection UI only, plus Job Order required at form level.

## Static validation
- Python source compilation: PASS.
- Dashboard template checked for nested forms: PASS (maintenance forms are outside container-create form).
- Recent-container links use the existing `container_detail` route.
- Product-master sync/upload routes are unchanged.
- No model/service/business-rule changes.
- No new migration.

## Runtime validation to run during upgrade
- `python manage.py migrate`
- `python manage.py check`

## Expected operator flow
1. Home opens with Recent containers on the left.
2. Click any container card to open it directly.
3. Search filters the visible recent-container cards without a server request.
4. New container form remains on the right and requires Container ID, Customer, Container date and Job Order.
5. Product master for the selected customer updates dynamically as before.
