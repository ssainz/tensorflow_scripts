import tensorflow as tf
import csv
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

def get_one_hot_class(sentiment):
    if sentiment == 'postive':
        return np.array([0,1])
    else:
        if sentiment == 'negative':
            return np.array([1,0])
        else:
            return np.array([0,0])



# Load sentences
def load_sentences(sentence_file, words):
    _Y = []
    _X = []
    with open(sentence_file, 'rt') as f:
        for line in f:
            tokens = line.split(',')
            _Y.append(get_one_hot_class(tokens[0]))
            sentence = ','.join(tokens[1:])
            sentence = sentence.replace("\n", "")
            tokens = sentence.split(' ')
            sequence = [words[token] for token in tokens]
            # Here we need to extend if len(sequence) < 100
            if len(sequence) < 100:
                missing = 100 - len(sequence)
                for j in range(missing):
                    sequence.append(np.zeros(shape=(50), dtype=np.float32))
            _X.append(sequence)
    return (np.stack(_X).transpose([0,2,1]), np.stack(_Y))


# Load word vectors
def load_word_vector(word_vector_file):
    word_vectors = {}
    with open(word_vector_file, 'rt') as f:
        word_vectors_reader = csv.reader(f, delimiter=',')
        for row in word_vectors_reader:
            # read the word
            word = row[0]
            # read the number vector, although is string initially
            vector_str = row[1:]
            # convert the string vector to fload vector
            vector_float = np.array([float(val) for val in vector_str])
            word_vectors[word] = vector_float
    return word_vectors

# Create Vanilla RNN:
def create_lstm_rnn(size_of_h_t, size_of_input_x, size_of_output_y, time_steps):

    X = tf.placeholder(shape=(size_of_input_x, time_steps, None), dtype=tf.float32)
    Y_hat = tf.placeholder(shape=(size_of_output_y, None), dtype=tf.float32)
    C_0 = tf.placeholder(shape=(size_of_h_t, None), dtype=tf.float32)
    h_0  = tf.placeholder(shape=(size_of_h_t, None), dtype=tf.float32)

    # RNN weights
    # Input gate:
    W_i = tf.Variable(tf.random_normal([size_of_h_t, size_of_input_x + size_of_h_t], stddev=0.1), name="W_i")
    b_i = tf.Variable(tf.random_normal([size_of_h_t, 1], stddev=0.1), name="b_i")

    # New state gate:
    W_c = tf.Variable(tf.random_normal([size_of_h_t, size_of_input_x + size_of_h_t], stddev=0.1), name="W_c")
    b_c = tf.Variable(tf.random_normal([size_of_h_t, 1], stddev=0.1), name="b_c")

    # Forget gate:
    W_f = tf.Variable(tf.random_normal([size_of_h_t, size_of_input_x + size_of_h_t], stddev=0.1), name="W_f")
    b_f = tf.Variable(tf.random_normal([size_of_h_t,1], stddev=0.1), name="b_f")

    # LSTM cell output gate:
    W_o = tf.Variable(tf.random_normal([size_of_h_t, size_of_input_x + size_of_h_t], stddev=0.1), name="W_o")
    b_o = tf.Variable(tf.random_normal([size_of_h_t, 1], stddev=0.1), name="b_o")

    # Actual output weights
    W_out = tf.Variable(tf.random_normal([size_of_output_y, size_of_h_t], stddev=0.1), name="W_out")
    b_out = tf.Variable(tf.random_normal([size_of_output_y, 1], stddev=0.1), name="b_out")



    x_slices_per_time_step = tf.unstack(X, axis=1) # each slice will be of shape (size_of_input_x, batch_size)

    # Create recurrences:
    first = True

    for x_slice_per_time_step in x_slices_per_time_step:
        if first:
            # The initial state is used just once! the first time

            # Create concatenation of X for this time step and h_t
            x_AND_h_t = tf.concat([x_slice_per_time_step, h_0], axis=0)

            # Use C_0 as C_t
            C_t = C_0

            first = False
        else:
            # h_t calculates again, and again and so on

            x_AND_h_t = tf.concat([x_slice_per_time_step, h_t], axis=0)

        # Forget gate:
        forget = tf.sigmoid(tf.matmul(W_f, x_AND_h_t) + b_f)

        # Input gate
        input = tf.sigmoid(tf.matmul(W_i, x_AND_h_t) + b_i)

        # New state:
        C_new = tf.tanh(tf.matmul(W_c, x_AND_h_t) + b_c)

        # Update C_t
        C_t = tf.multiply(forget, C_t) + tf.multiply(input, C_new)

        # Output gate
        output = tf.sigmoid(tf.matmul(W_o, x_AND_h_t) + b_o)

        # Update h_t
        h_t = tf.multiply(output, tf.tanh(C_t))


    # Just one final prediction (no intermediate predictions):
    y_pre_softmax = tf.matmul(W_out, h_t) + b_out

    y = tf.nn.softmax(y_pre_softmax, dim=0)

    # Calculate loss:
    cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=Y_hat, logits=y_pre_softmax, dim=0)
    loss = tf.reduce_mean(cross_entropy)

    # Optimization
    eta = 1e-4
    train = tf.train.AdamOptimizer(eta).minimize(loss)

    # Accuracy:
    correct_prediction = tf.equal(tf.argmax(y, 0), tf.argmax(Y_hat, 0))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    return (X, Y_hat, h_0, C_0, y, y_pre_softmax, train, accuracy, loss)

batch_size = 10
size_of_h_t = 100
(X, Y_hat, h_0, C_0, y, y_pre_softmax, train, accuracy, loss) = create_lstm_rnn(size_of_h_t = size_of_h_t,
                                                       size_of_input_x = 50,
                                                       size_of_output_y = 2,
                                                       time_steps = 100)


# Load word vector file:
words = load_word_vector("/srv/datasets/sentiment-data/word-vectors-refine.txt")

# Load the training set
(_x_training, _y_training) = load_sentences("/srv/datasets/sentiment-data/train.csv", words)


# Start training:
init = tf.global_variables_initializer()
sess = tf.Session()
sess.run(init)

initial_h_0 = initial_C_0 = np.zeros(shape=(size_of_h_t, batch_size), dtype=np.float32)

lstm_training_loss = []
lstm_training_accuracy = []
for z in range(1):
    i = 0
    while i < len(_x_training):
        # sample_y will be a [2, batch_size] tensor
        next_i = i + batch_size
        sample_y = _y_training[i:next_i].transpose()
        # sample_x will be a [50, 100, batch_size] tensor
        sample_x = _x_training[i:next_i].transpose([1,2,0])

        #next iteration
        i = next_i

        [cur_traing, cur_loss, cur_accuracy, cur_y, cur_y_pre_softmax] = sess.run([train, loss, accuracy, y, y_pre_softmax],
                                                                                  {X: sample_x, Y_hat: sample_y, h_0: initial_h_0, C_0: initial_C_0})

        lstm_training_accuracy.append(cur_accuracy)
        lstm_training_loss.append(cur_loss)

        print("It[%s], loss [%s], accuracy [%s] " % (i, cur_loss, cur_accuracy))

# Load the testing set

(_x_test, _y_test) = load_sentences("/srv/datasets/sentiment-data/test.csv", words)
sample_y = _y_test.transpose()
sample_x = _x_test.transpose([1,2,0])
test_initial_h_0 = test_initial_C_0 = np.zeros(shape=(size_of_h_t, sample_x.shape[2]), dtype=np.float32)
[test_loss, test_accuracy] = sess.run([loss, accuracy], {X: sample_x, Y_hat: sample_y, h_0: test_initial_h_0, C_0: test_initial_C_0})
print("Testing loss[%s] accuracy [%s]" % (test_loss, test_accuracy))

# Print the training performance
plt.subplot(2, 1, 1)
label_training_cost, = plt.plot(np.array(lstm_training_loss), label='lstm_rnn_training_loss')
plt.legend(handles=[label_training_cost])
plt.subplot(2, 1, 2)
label_training_accuracy, = plt.plot(np.array(lstm_training_accuracy), label='lstm_rnn_training_accuracy')
plt.legend(handles=[label_training_accuracy])
plt.draw()
plt.show()