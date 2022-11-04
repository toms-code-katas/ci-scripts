# See https://www.tensorflow.org/tutorials/keras/text_classification
import numpy as np
import re
import string

import tensorflow as tf
from keras import layers, losses

if __name__ == '__main__':
    tf.config.set_visible_devices([], 'GPU')

    batch_size = 32
    seed = 42

    data_dir = '/tmp/data-ENZ6HK'
    raw_train_ds = tf.keras.utils.text_dataset_from_directory(
        data_dir,
        batch_size=batch_size,
        validation_split=0.2,
        subset='training',
        seed=seed)

    for text_batch, label_batch in raw_train_ds.take(1):
        for i in range(3):
            print("Trace", text_batch.numpy()[i])
            print("Label", label_batch.numpy()[i])

    raw_val_ds = tf.keras.utils.text_dataset_from_directory(
        data_dir,
        batch_size=batch_size,
        validation_split=0.2,
        subset='validation',
        seed=seed)

    raw_test_ds = tf.keras.utils.text_dataset_from_directory(
        data_dir,
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
    print("Vectorized review", vectorize_text(first_trace, first_label))

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
    failure_test_trace = Path('/tmp/data-ENZ6HK/failed/3202596907.txt').read_text()
    success_test_trace = Path('/tmp/data-ENZ6HK/success/3246658345.txt').read_text()

    samples_to_predict = np.array(["", failure_test_trace, success_test_trace, "Job failed: exit code 1", "Job succeeded", "Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded Job succeeded"])

    result = export_model.predict(samples_to_predict, verbose=2)
    print(result)

