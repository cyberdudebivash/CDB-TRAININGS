import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Objects;
/** Pure local Java test target. Monetary rounding happens once at the final line. */
public final class OrderCalculator {
    private OrderCalculator() {}
    public static BigDecimal total(BigDecimal unitPrice, int quantity, BigDecimal discountRate) {
        Objects.requireNonNull(unitPrice, "unitPrice");
        Objects.requireNonNull(discountRate, "discountRate");
        if (unitPrice.signum() < 0 || quantity < 0) throw new IllegalArgumentException("negative price or quantity");
        if (discountRate.signum() < 0 || discountRate.compareTo(BigDecimal.ONE) > 0)
            throw new IllegalArgumentException("discount must be in [0, 1]");
        return unitPrice.multiply(BigDecimal.valueOf(quantity))
                .multiply(BigDecimal.ONE.subtract(discountRate))
                .setScale(2, RoundingMode.HALF_EVEN);
    }
}
