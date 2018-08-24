import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.*;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.CoreMatchers.*;

public class PrimeCheckerTest {
    @Test
    public void oneIsNotPrime() {
        // but the naive prime checker thinks it is, this should fail
        assertThat(PrimeChecker.isPrime(1), is(false));
    }

    @Test
    public void isPrimeTrueForPrimes() {
        int[] primes = {3, 5, 7, 97, 131, 197, 541};

        for (int prime : primes) {
            assertThat(PrimeChecker.isPrime(prime), is(true));
        }
    }

    @Test
    public void isPrimeFalseForComposites() {
        int[] composites = {4, 6, 9, 25, 105, 437, 529};

        for (int composite : composites) {
            assertThat(PrimeChecker.isPrime(composite), is(false));
        }
    }
}
