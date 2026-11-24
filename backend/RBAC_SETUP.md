# Stratov role-based access control setup

## Roles

- **Admin**: full access, user role management, account activation/deactivation, and audit logs.
- **Product Manager**: create and manage product data, feedback analysis, prioritization, PRDs, roadmap, strategy reports, and chat.
- **Developer**: read workspace information and update existing roadmap/features using `PUT` or `PATCH`; cannot create/delete product records or administer users.
- **Executive**: read-only access to workspace information and executive strategy reporting.

The React route guard improves navigation, but the FastAPI middleware is the security boundary. Do not rely on hidden buttons or routes as authorization.

## First administrator

1. Register the account that should become the first administrator.
2. Stop the backend or run this command from the `backend/` directory with the backend virtual environment active:

   ```bash
   python scripts/promote_admin.py --email you@example.com
   ```

3. Type `PROMOTE` when prompted.
4. Sign out and sign in again. The account will now have the `Admin` role.
5. Open the profile menu and select **User administration** to assign roles to other accounts.

The script only promotes an existing account. It does not create a password or expose an unauthenticated admin endpoint.

## Registration and role assignment

Public registration always creates a Product Manager account. The role submitted by a browser is ignored. Only an authenticated Admin can assign one of the four supported roles. Existing legacy labels are normalized when read: Product Owner, Product Lead, Senior Product Manager map to Product Manager; Analyst maps to Executive.

## Notes

- Account deactivation is enforced on subsequent API requests and the next login is rejected.
- The last active Admin cannot be demoted or deactivated.
- Role and account-status changes are recorded in the `audit_logs` MongoDB collection.
- Existing workspace ownership filters remain in place; RBAC does not grant users access to another user's records.
- `Sidebar.jsx` is intentionally unchanged. Unauthorized pages are blocked by route guards, even if an old navigation link remains visible.
- The frontend mock mode has a demo-only Admin account (`admin@copilot.com`, password `Admin123!`). Mock mode is browser-local and is not production authentication.
