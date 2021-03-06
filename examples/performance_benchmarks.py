#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""This file contains tests of code performance to reveal bottlenecks."""
import numpy
import time

from openfermion.ops import (FermionOperator,
                             InteractionOperator,
                             normal_ordered)
from openfermion.transforms import get_fermion_operator, jordan_wigner
from openfermion.utils import jordan_wigner_sparse


def artificial_molecular_operator(n_qubits):
    """Make an artificial random InteractionOperator for testing purposes."""

    # Initialize.
    constant = numpy.random.randn()
    one_body_coefficients = numpy.zeros((n_qubits, n_qubits), float)
    two_body_coefficients = numpy.zeros((n_qubits, n_qubits,
                                         n_qubits, n_qubits), float)

    # Randomly generate the one-body and two-body integrals.
    for p in range(n_qubits):
        for q in range(n_qubits):

            # One-body terms.
            if (p <= p) and (p % 2 == q % 2):
                one_body_coefficients[p, q] = numpy.random.randn()
                one_body_coefficients[q, p] = one_body_coefficients[p, q]

            # Keep looping.
            for r in range(n_qubits):
                for s in range(n_qubits):

                    # Skip zero terms.
                    if (p == q) or (r == s):
                        continue

                    # Identify and skip one of the complex conjugates.
                    if [p, q, r, s] != [s, r, q, p]:
                        unique_indices = len(set([p, q, r, s]))

                        # srqp srpq sprq spqr sqpr sqrp
                        # rsqp rspq rpsq rpqs rqps rqsp.
                        if unique_indices == 4:
                            if min(r, s) <= min(p, q):
                                continue

                        # qqpp.
                        elif unique_indices == 2:
                            if q < p:
                                continue

                    # Add the two-body coefficients.
                    two_body_coefficients[p, q, r, s] = numpy.random.randn()
                    two_body_coefficients[s, r, q, p] = two_body_coefficients[
                        p, q, r, s]

    # Build the molecular operator and return.
    molecular_operator = InteractionOperator(
        constant, one_body_coefficients, two_body_coefficients)
    return molecular_operator


def benchmark_molecular_operator_jordan_wigner(n_qubits):
    """Test speed with which molecular operators transform to qubit operators.

    Args:
        n_qubits: The size of the molecular operator instance. Ideally, we
            would be able to transform to a qubit operator for 50 qubit
            instances in less than a minute. We are way too slow right now.

    Returns:
        runtime: The number of seconds required to make the conversion.
    """
    # Get an instance of InteractionOperator.
    molecular_operator = artificial_molecular_operator(n_qubits)

    # Convert to a qubit operator.
    start = time.time()
    qubit_operator = jordan_wigner(molecular_operator)
    end = time.time()

    # Return runtime.
    runtime = end - start
    return runtime


def benchmark_fermion_math_and_normal_order(n_qubits, term_length, power):
    """Benchmark both arithmetic operators and normal ordering on fermions.

    The idea is we generate two random FermionTerms, A and B, each acting
    on n_qubits with term_length operators. We then compute
    (A + B) ** power. This is costly that is the first benchmark. The second
    benchmark is in normal ordering whatever comes out.

    Args:
        n_qubits: The number of qubits on which these terms act.
        term_length: The number of operators in each term.
        power: Int, the exponent to which to raise sum of the two terms.

    Returns:
        runtime_math: The time it takes to perform (A + B) ** power
        runtime_normal_order: The time it takes to perform
            FermionOperator.normal_order()
    """
    # Generate random operator strings.
    operators_a = [(numpy.random.randint(n_qubits),
                    numpy.random.randint(2))]
    operators_b = [(numpy.random.randint(n_qubits),
                    numpy.random.randint(2))]
    for operator_number in range(term_length):

        # Make sure the operator is not trivially zero.
        operator_a = (numpy.random.randint(n_qubits),
                      numpy.random.randint(2))
        while operator_a == operators_a[-1]:
            operator_a = (numpy.random.randint(n_qubits),
                          numpy.random.randint(2))
        operators_a += [operator_a]

        # Do the same for the other operator.
        operator_b = (numpy.random.randint(n_qubits),
                      numpy.random.randint(2))
        while operator_b == operators_b[-1]:
            operator_b = (numpy.random.randint(n_qubits),
                          numpy.random.randint(2))
        operators_b += [operator_b]

    # Initialize FermionTerms and then sum them together.
    fermion_term_a = FermionOperator(tuple(operators_a),
                                     float(numpy.random.randn()))
    fermion_term_b = FermionOperator(tuple(operators_b),
                                     float(numpy.random.randn()))
    fermion_operator = fermion_term_a + fermion_term_b

    # Exponentiate.
    start_time = time.time()
    fermion_operator **= power
    runtime_math = time.time() - start_time

    # Normal order.
    start_time = time.time()
    normal_ordered(fermion_operator)
    runtime_normal_order = time.time() - start_time

    # Return.
    return runtime_math, runtime_normal_order


def benchmark_jordan_wigner_sparse(n_qubits):
    """Benchmark the speed at which a FermionOperator is mapped to a matrix.

    Args:
        n_qubits: The number of qubits in the example.

    Returns:
        runtime: The time in seconds that the benchmark took.
    """
    # Initialize a random FermionOperator.
    molecular_operator = artificial_molecular_operator(n_qubits)
    fermion_operator = get_fermion_operator(molecular_operator)

    # Map to SparseOperator class.
    start_time = time.time()
    sparse_operator = jordan_wigner_sparse(fermion_operator)
    runtime = time.time() - start_time
    return runtime


# Run benchmarks.
if __name__ == '__main__':

    # Seed random number generator.
    numpy.random.seed(8)

    # Run InteractionOperator.jordan_wigner_transform() benchmark.
    n_qubits = 18
    print('Starting test on InteractionOperator.jordan_wigner_transform()')
    runtime = benchmark_molecular_operator_jordan_wigner(n_qubits)
    print('InteractionOperator.jordan_wigner_transform() ' +
          'takes {} seconds on {} qubits.\n'.format(runtime, n_qubits))

    # Run benchmark on FermionOperator math and normal-ordering.
    n_qubits = 20
    term_length = 10
    power = 15
    print('Starting test on FermionOperator math and normal ordering.')
    runtime_math, runtime_normal = benchmark_fermion_math_and_normal_order(
        n_qubits, term_length, power)
    print('Math took {} seconds. Normal ordering took {} seconds.\n'.format(
        runtime_math, runtime_normal))

    # Run FermionOperator.jordan_wigner_sparse() benchmark.
    n_qubits = 10
    print('Starting test on FermionOperator.jordan_wigner_sparse().')
    runtime = benchmark_jordan_wigner_sparse(n_qubits)
    print('Construction of SparseOperator took {} seconds.'.format(
        runtime))
