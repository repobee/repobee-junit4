package se.repobee.fibo;
/**
 * Class for calculating Fibonacci numbers.
 */

public class Fibo {
    private long prev;
    private long current;

    public Fibo() {
        prev = 0;
        current = 1;
    }

    /**
     * Generate the next Fibonacci number.
     */
    public long next() {
        long ret = prev;
        prev = current;
        current = ret + current;
        return ret;
    }
}
