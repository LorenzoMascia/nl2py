def block_3(context: dict) -> dict:
    total_sales = sum(context.get(key, 0) for key in context if key.startswith('amount_'))
    context["total_sales"] = total_sales
    return context