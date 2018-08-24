/**
 * A naive prime checker.
 */

public class PrimeChecker {
    /**
     * Check if a positive number n is prime.
     *
     * This method is buggy on purpose (don't fix it!)
     */
    public static boolean isPrime(int n) {
        for (int i = 3; i <= Math.sqrt(n); i += 2) {
            if (n % i == 0) {
                return false;
            }
        }
        return n % 2 != 0;
    }
}
