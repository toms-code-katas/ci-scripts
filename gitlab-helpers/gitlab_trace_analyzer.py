# See https://www.tensorflow.org/tutorials/keras/text_classification
import numpy as np
import os
import re
import string

import tensorflow as tf
from keras import layers, losses

if __name__ == '__main__':

    tf.config.set_visible_devices([], 'GPU')

    batch_size = 32
    seed = 42

    data_dir = '/tmp/trace-data-Bd4pvA/train'
    raw_train_ds = tf.keras.utils.text_dataset_from_directory(
        data_dir,
        batch_size=batch_size,
        validation_split=0.2,
        subset='training',
        seed=seed)

    print("Label 0 corresponds to", raw_train_ds.class_names[0])
    print("Label 1 corresponds to", raw_train_ds.class_names[1])

    raw_val_ds = tf.keras.utils.text_dataset_from_directory(
        data_dir,
        batch_size=batch_size,
        validation_split=0.2,
        subset='validation',
        seed=seed,
        shuffle=False)

    raw_test_ds = tf.keras.utils.text_dataset_from_directory(
        '/tmp/trace-data-Bd4pvA/test',
        batch_size=batch_size)


    def custom_standardization(input_data):
        lowercase = tf.strings.lower(input_data)
        return tf.strings.regex_replace(lowercase, '[%s]' % re.escape(string.punctuation), '')


    max_features = 10000
    sequence_length = 250

    vectorize_layer = layers.TextVectorization(
        standardize=custom_standardization,
        max_tokens=max_features,
        output_mode='int',
        output_sequence_length=sequence_length)

    train_text = raw_train_ds.map(lambda x, y: x)
    vectorize_layer.adapt(train_text)

    def vectorize_text(text, label):
        text = tf.expand_dims(text, -1)
        return vectorize_layer(text), label


    text_batch, label_batch = next(iter(raw_train_ds))
    first_trace, first_label = text_batch[0], label_batch[0]
    print("Trace", first_trace)
    print("Label", raw_train_ds.class_names[first_label])
    print("Vectorized trace", vectorize_text(first_trace, first_label))

    print('Vocabulary size: {}'.format(len(vectorize_layer.get_vocabulary())))

    train_ds = raw_train_ds.map(vectorize_text)
    val_ds = raw_val_ds.map(vectorize_text)
    test_ds = raw_test_ds.map(vectorize_text)

    embedding_dim = 16
    model = tf.keras.Sequential([
        layers.Embedding(max_features + 1, embedding_dim),
        layers.Dropout(0.2),
        layers.GlobalAveragePooling1D(),
        layers.Dropout(0.2),
        layers.Dense(1)])

    model.summary()

    model.compile(loss=losses.BinaryCrossentropy(from_logits=True),
                  optimizer='adam',
                  metrics=tf.metrics.BinaryAccuracy(threshold=0.0))

    epochs = 10
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs)

    export_model = tf.keras.Sequential([
      vectorize_layer,
      model,
      layers.Activation('sigmoid')
    ])

    loss, accuracy = model.evaluate(test_ds)

    print("Loss: ", loss)
    print("Accuracy: ", accuracy)

    export_model = tf.keras.Sequential([
      vectorize_layer,
      model,
      layers.Activation('sigmoid')
    ])

    export_model.compile(
        loss=losses.BinaryCrossentropy(from_logits=False), optimizer="adam", metrics=['accuracy']
    )

    from pathlib import Path

    samples_to_predict = np.array(["success", "failed", "I Failed my vocabulary test", "Success is not an option"])

    predictions = export_model.predict(samples_to_predict, verbose=2)
    test = (predictions > 0.5).astype('int32')
    print(test)
