class KnowledgeBaseService:
    """Flattens a venue's knowledge base into plain text for an LLM system prompt.

    A future RAG-based retrieval implementation can replace build_context's body
    without callers changing, as long as it keeps returning a single text block.
    """

    @staticmethod
    def build_context(venue):
        sections = [f'Venue: {venue.name}']
        if venue.description:
            sections.append(venue.description)

        event_types = venue.eventtype_set.all()
        if event_types:
            lines = [f'- {et.name} ({et.min_guests}-{et.max_guests} guests)' for et in event_types]
            sections.append('Event types:\n' + '\n'.join(lines))

        packages = venue.package_set.select_related('event_type')
        if packages:
            lines = [f'- {pkg.name}: R$ {pkg.base_price} - {pkg.description}' for pkg in packages]
            sections.append('Packages:\n' + '\n'.join(lines))

        menus = venue.menu_set.prefetch_related('items')
        if menus:
            lines = []
            for menu in menus:
                items = ', '.join(item.name for item in menu.items.all())
                lines.append(f'- {menu.name}: {items}')
            sections.append('Menus:\n' + '\n'.join(lines))

        decorations = venue.decorationoption_set.all()
        if decorations:
            lines = [f'- {opt.name}: R$ {opt.price} - {opt.description}' for opt in decorations]
            sections.append('Decoration options:\n' + '\n'.join(lines))

        faqs = venue.faq_set.all()
        if faqs:
            lines = [f'Q: {faq.question}\nA: {faq.answer}' for faq in faqs]
            sections.append('FAQs:\n' + '\n'.join(lines))

        if venue.payment_policy:
            sections.append(f'Payment policy: {venue.payment_policy}')
        if venue.cancellation_policy:
            sections.append(f'Cancellation policy: {venue.cancellation_policy}')
        if venue.parking_info:
            sections.append(f'Parking: {venue.parking_info}')

        return '\n\n'.join(sections)
