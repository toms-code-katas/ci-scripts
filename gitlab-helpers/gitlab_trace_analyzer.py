# See https://www.tensorflow.org/tutorials/keras/text_classification
import os
import tensorflow as tf

if __name__ == '__main__':
    tf.config.set_visible_devices([], 'GPU')

    batch_size = 32
    seed = 42

    raw_train_ds = tf.keras.utils.text_dataset_from_directory(
        '/tmp/data-UDKTW4',
        batch_size=batch_size,
        validation_split=0.2,
        subset='training',
        seed=seed)
