# Database Structure

EasyPick DB is now organized around two flows:

- `001_schema.sql`: bootstrap schema for a fresh PostgreSQL volume
- `002_seed.sql`: demo seed data for categories, products, reviews, and default AI settings
- `migrations/*.sql`: incremental schema changes applied by the backend at startup

## Core Tables

- `categories`: product category master
- `products`: catalog items with JSONB specs and descriptive fields
- `reviews`: product reviews
- `shopping_sessions`: browser/session level ownership for carts and order history
- `cart_items`: session cart items
- `orders`: order header
- `order_items`: order line snapshot
- `order_status_history`: append-only order status audit log
- `inventory_transactions`: append-only stock change history
- `ai_settings`: singleton AI provider configuration
- `ai_logs`: AI request/response history
- `schema_migrations`: applied migration versions

## Maintenance Rules

- Put the latest fresh-install schema in `001_schema.sql`.
- Put only demo/bootstrap data in `002_seed.sql`.
- Put all changes for existing databases in a new `migrations/<version>.sql` file.
- Keep migrations additive and idempotent where practical.
- Prefer audit inserts over destructive history updates for orders and inventory.
