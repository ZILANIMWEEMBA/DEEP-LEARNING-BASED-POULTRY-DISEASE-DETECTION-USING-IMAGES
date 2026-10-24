# Administrator manual
The first admin is created from `ADMIN_EMAIL/ADMIN_PASSWORD` in `.env`. **Overview**: totals, disease distribution, recent activity.
**Users**: filter, activate/deactivate (you cannot deactivate yourself), create users incl. admins. **Records**: all poultry and predictions
(image files are not exposed here). **Knowledge & medication**: view disease info; add medication *reference* categories (no dosing).
**Model**: availability, metadata, and real evaluation results (or "not yet available"). **Logs & notifications**: audit trail and broadcasts.
Operations: back up `database/poultry.db` and `uploads/`; rotate `SECRET_KEY` only when users can re-login (tokens become invalid).
