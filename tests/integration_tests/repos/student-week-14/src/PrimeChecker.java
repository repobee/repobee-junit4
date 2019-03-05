/**
 * A naive prime checker.
 */

public class PrimeChecker {
    /**
     * Check if a positive number n is prime.
     */
    public static boolean isPrime(int n) {
        if (n <= 2) {
            return n == 2;
        } else if (n % 2 == 0) {
            return false;
        }

        for (int i = 3; i <= Math.sqrt(n); i += 2) {
            if (n % i == 0) {
                return false;
            }
        }
        return true;
    }
}
