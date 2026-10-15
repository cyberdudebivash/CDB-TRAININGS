import java.math.BigDecimal;
/** Zero-dependency boundary contract for Java 21+. Not a replacement for JUnit coursework. */
public final class OrderCalculatorTest {
    private static int checks = 0;
    private static void eq(String expected, BigDecimal actual) {
        checks++;
        if (new BigDecimal(expected).compareTo(actual) != 0) throw new AssertionError(expected+" != "+actual);
    }
    private static void fails(Runnable run) {
        checks++;
        try { run.run(); } catch (IllegalArgumentException | NullPointerException expected) {return;}
        throw new AssertionError("Expected input validation failure");
    }
    public static void main(String[] args) {
        eq("200.00", OrderCalculator.total(new BigDecimal("100.00"),2,BigDecimal.ZERO));
        eq("90.00", OrderCalculator.total(new BigDecimal("50.00"),2,new BigDecimal("0.10")));
        eq("0.00", OrderCalculator.total(new BigDecimal("999.99"),0,BigDecimal.ZERO));
        eq("0.00", OrderCalculator.total(new BigDecimal("999.99"),1,BigDecimal.ONE));
        eq("0.02", OrderCalculator.total(new BigDecimal("0.025"),1,BigDecimal.ZERO));
        fails(()->OrderCalculator.total(new BigDecimal("-1"),1,BigDecimal.ZERO));
        fails(()->OrderCalculator.total(BigDecimal.ONE,-1,BigDecimal.ZERO));
        fails(()->OrderCalculator.total(BigDecimal.ONE,1,new BigDecimal("1.01")));
        fails(()->OrderCalculator.total(BigDecimal.ONE,1,new BigDecimal("-0.01")));
        fails(()->OrderCalculator.total(null,1,BigDecimal.ZERO));
        System.out.println("PASS: "+checks+" Java contract checks");
    }
}
