from models import Offer


class OfferService:
    @staticmethod
    def get_active_offers():
        return Offer.query.filter_by(is_active=True).order_by(Offer.quantity.desc()).all()

    @staticmethod
    def calculate_total_with_offers(num_items, unit_price, offers):
        """
        Calcula el total aplicando ofertas por cantidad de forma greedy
        (primero packs más grandes). Asume que todos los cursos valen lo mismo.
        """
        remaining = num_items
        total = 0.0
        applied = []

        sorted_offers = sorted(offers, key=lambda o: o.quantity, reverse=True)

        for offer in sorted_offers:
            if remaining <= 0:
                break
            qty = offer.quantity or 0
            if qty <= 0:
                continue

            packs = remaining // qty
            if packs > 0:
                total += packs * offer.price
                remaining -= packs * qty
                applied.append(
                    {
                        "quantity": qty,
                        "price": offer.price,
                        "packs": packs,
                    }
                )

        if remaining > 0:
            total += remaining * unit_price

        return {
            "total": total,
            "remaining": remaining,
            "applied_offers": applied,
        }

