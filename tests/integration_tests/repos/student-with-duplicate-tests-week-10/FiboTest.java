import static org.hamcrest.CoreMatchers.*;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.junit.Assert.*;

import org.junit.Before;
import org.junit.Test;

public class FiboTest {
    @Test
    public void correctlyGeneratesFirst10Numbers() {
        Fibo f = new Fibo();
        long[] expected = {0, 1, 1, 2, 3, 5, 8, 13, 21, 34};
        long[] actual = new long[10];

        for (int i = 0; i < 10; i++) {
            actual[i] = f.next();
        }

        assertThat(actual, equalTo(expected));
    }

    @Test
    public void correctlyGeneratesFiftiethNumber() {
        // note that the first number is counted as the 0th
        Fibo f = new Fibo();

        for (int i = 0; i < 50; i++) {
            f.next();
        }

        assertThat(f.next(), equalTo(12586269025l));
    }
}
