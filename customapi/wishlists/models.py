from oscar.apps.wishlists.abstract_models import (AbstractWishList)


class WishList(AbstractWishList):

    def add(self, product, title=None, quantity=None):
        """
        Add a product to this wishlist
        """
        lines = self.lines.filter(product=product)
        if len(lines) == 0:
            self.lines.create(
                product=product, title=title, quantity=int(quantity))
        else:
            line = lines[0]
            line.quantity += int(quantity) if int(quantity) else 1
            line.save()

    def remove(self, product):
        """
        Remove a product from this wishlist
        """
        lines = self.lines.filter(product=product)
        if len(lines) == 0:
            return
        else:
            line = lines[0]
            line.delete()

    def get_lines(self):
        return self.lines


from oscar.apps.wishlists.models import *