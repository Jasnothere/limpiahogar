-- =====================================================================
-- PROYECTO : Sistema de servicios de aseo en viviendas (LimpiaHogar)
-- ARCHIVO  : 15 consultas preparadas (PostgreSQL / pgAdmin 4)
--
-- Cómo usarlo en pgAdmin 4:
--   1. Ejecutar aseo-viviendas.sql   (crea las tablas)
--   2. Ejecutar datos-prueba.sql     (carga los datos de prueba)
--   3. Abrir este archivo en el Query Tool, seleccionar una consulta
--      y pulsar F5 (o ejecutar todo el archivo).
--
-- Las mismas consultas se pueden ver ejecutadas en la aplicación web,
-- en la página "Consultas SQL".
-- =====================================================================


-- Consulta 1: Selección con filtro y ordenamiento
-- Clientes activos ordenados por apellido y nombre.
SELECT id_cliente, documento, nombre, apellido, telefono, correo
FROM cliente
WHERE estado = 'activo'
ORDER BY apellido, nombre;


-- Consulta 2: Filtro con BETWEEN e ILIKE
-- Tipos de servicio con precio entre $50.000 y $100.000 cuyo nombre contiene "limpieza".
SELECT nombre, duracion_horas, precio
FROM tipo_servicio
WHERE precio BETWEEN 50000 AND 100000
  AND nombre ILIKE '%limpieza%'
ORDER BY precio;


-- Consulta 3: INNER JOIN de varias tablas
-- Servicios con el cliente, la dirección, el barrio y la zona donde se prestan.
SELECT s.id_servicio, s.fecha, s.hora_inicio, s.estado,
       c.nombre || ' ' || c.apellido AS cliente,
       v.direccion, b.nombre AS barrio, z.nombre AS zona
FROM servicio s
JOIN vivienda v ON v.id_vivienda = s.id_vivienda
JOIN cliente  c ON c.id_cliente  = v.id_cliente
JOIN barrio   b ON b.id_barrio   = v.id_barrio
JOIN zona     z ON z.id_zona     = b.id_zona
ORDER BY s.fecha DESC, s.hora_inicio;


-- Consulta 4: LEFT JOIN con conteo (incluye a quienes no tienen servicios)
-- Número de servicios solicitados por cada cliente, incluidos los que tienen 0.
SELECT c.id_cliente, c.nombre || ' ' || c.apellido AS cliente,
       COUNT(s.id_servicio) AS total_servicios
FROM cliente c
LEFT JOIN vivienda v ON v.id_cliente  = c.id_cliente
LEFT JOIN servicio s ON s.id_vivienda = v.id_vivienda
GROUP BY c.id_cliente, c.nombre, c.apellido
ORDER BY total_servicios DESC, cliente;


-- Consulta 5: GROUP BY con varias columnas
-- Cantidad de servicios por zona y por estado.
SELECT z.nombre AS zona, s.estado, COUNT(*) AS cantidad
FROM servicio s
JOIN vivienda v ON v.id_vivienda = s.id_vivienda
JOIN barrio   b ON b.id_barrio   = v.id_barrio
JOIN zona     z ON z.id_zona     = b.id_zona
GROUP BY z.nombre, s.estado
ORDER BY z.nombre, s.estado;


-- Consulta 6: Funciones de agregación con fechas (SUM, COUNT, AVG)
-- Ingresos por mes: número de pagos, total y pago promedio.
SELECT TO_CHAR(DATE_TRUNC('month', p.fecha), 'YYYY-MM') AS mes,
       COUNT(*)              AS pagos,
       SUM(p.monto)          AS total,
       ROUND(AVG(p.monto), 0) AS promedio
FROM pago p
GROUP BY DATE_TRUNC('month', p.fecha)
ORDER BY mes;


-- Consulta 7: GROUP BY con HAVING
-- Empleados con calificación promedio de 4 o más y al menos 3 calificaciones.
SELECT e.nombre || ' ' || e.apellido AS empleado,
       COUNT(a.calificacion_empleado)        AS calificaciones,
       ROUND(AVG(a.calificacion_empleado), 2) AS promedio
FROM empleado e
JOIN asignacion a ON a.id_empleado = e.id_empleado
WHERE a.calificacion_empleado IS NOT NULL
GROUP BY e.id_empleado, e.nombre, e.apellido
HAVING AVG(a.calificacion_empleado) >= 4 AND COUNT(a.calificacion_empleado) >= 3
ORDER BY promedio DESC;


-- Consulta 8: Subconsulta con IN
-- Empleados activos que pueden hacer la limpieza de piscina
-- (tienen la especialidad que exige ese tipo de servicio).
SELECT e.documento, e.nombre || ' ' || e.apellido AS empleado
FROM empleado e
WHERE e.estado = 'activo'
  AND e.id_empleado IN (
        SELECT ee.id_empleado
        FROM empleado_especialidad ee
        JOIN tipo_servicio ts ON ts.id_especialidad = ee.id_especialidad
        WHERE ts.nombre = 'Limpieza de piscina')
ORDER BY empleado;


-- Consulta 9: Subconsulta con NOT EXISTS
-- Viviendas que tienen piscina pero nunca han pedido la limpieza de piscina
-- (clientes a los que se les puede ofrecer ese servicio).
SELECT v.id_vivienda, v.direccion, c.nombre || ' ' || c.apellido AS cliente, c.telefono
FROM vivienda v
JOIN cliente c ON c.id_cliente = v.id_cliente
WHERE EXISTS (SELECT 1 FROM area a
              JOIN tipo_area ta ON ta.id_tipo_area = a.id_tipo_area
              WHERE a.id_vivienda = v.id_vivienda AND ta.nombre = 'Piscina')
  AND NOT EXISTS (SELECT 1 FROM servicio s
                  JOIN detalle_servicio d ON d.id_servicio = s.id_servicio
                  JOIN tipo_servicio ts  ON ts.id_tipo_servicio = d.id_tipo_servicio
                  WHERE s.id_vivienda = v.id_vivienda AND ts.nombre = 'Limpieza de piscina');


-- Consulta 10: Subconsulta en el FROM (tabla derivada)
-- Clientes con calificación promedio menor a 3 (candidatos a bloqueo, supuesto 15).
SELECT t.cliente, t.estado, t.calificaciones, t.promedio
FROM (SELECT c.nombre || ' ' || c.apellido AS cliente, c.estado,
             COUNT(a.calificacion_cliente)         AS calificaciones,
             ROUND(AVG(a.calificacion_cliente), 2) AS promedio
      FROM cliente c
      JOIN vivienda   v ON v.id_cliente  = c.id_cliente
      JOIN servicio   s ON s.id_vivienda = v.id_vivienda
      JOIN asignacion a ON a.id_servicio = s.id_servicio
      WHERE a.calificacion_cliente IS NOT NULL
      GROUP BY c.id_cliente, c.nombre, c.apellido, c.estado) AS t
WHERE t.promedio < 3
ORDER BY t.promedio;


-- Consulta 11: Auto-relación (self join)
-- Cada empleado con su supervisor y cuántas personas supervisa.
SELECT e.nombre || ' ' || e.apellido AS empleado, e.estado,
       COALESCE(s.nombre || ' ' || s.apellido, '(sin supervisor)') AS supervisor,
       (SELECT COUNT(*) FROM empleado x WHERE x.id_supervisor = e.id_empleado) AS supervisa_a
FROM empleado e
LEFT JOIN empleado s ON s.id_empleado = e.id_supervisor
ORDER BY supervisa_a DESC, empleado;


-- Consulta 12: Expresión CASE
-- Estado del inventario de insumos según el stock disponible.
SELECT i.nombre, ci.nombre AS categoria, p.nombre AS proveedor, i.stock,
       CASE
           WHEN i.stock < 100 THEN 'Crítico: pedir ya'
           WHEN i.stock < 300 THEN 'Bajo'
           ELSE 'Suficiente'
       END AS estado_inventario
FROM insumo i
JOIN categoria_insumo ci ON ci.id_categoria = i.id_categoria
JOIN proveedor p        ON p.id_proveedor  = i.id_proveedor
ORDER BY i.stock;


-- Consulta 13: UNION
-- Directorio de contactos: clientes, empleados y proveedores en una sola lista.
SELECT 'Cliente' AS tipo, nombre || ' ' || apellido AS nombre, telefono FROM cliente
UNION ALL
SELECT 'Empleado', nombre || ' ' || apellido, telefono FROM empleado
UNION ALL
SELECT 'Proveedor', nombre, telefono FROM proveedor
ORDER BY tipo, nombre;


-- Consulta 14: Función de ventana (RANK)
-- Ranking de empleados por horas trabajadas en servicios finalizados.
SELECT RANK() OVER (ORDER BY SUM(ts.duracion_horas) DESC) AS puesto,
       e.nombre || ' ' || e.apellido AS empleado,
       COUNT(DISTINCT s.id_servicio) AS servicios,
       SUM(ts.duracion_horas)        AS horas
FROM empleado e
JOIN asignacion a       ON a.id_empleado = e.id_empleado
JOIN servicio s         ON s.id_servicio = a.id_servicio AND s.estado = 'finalizado'
JOIN detalle_servicio d ON d.id_servicio = s.id_servicio
JOIN tipo_servicio ts   ON ts.id_tipo_servicio = d.id_tipo_servicio
GROUP BY e.id_empleado, e.nombre, e.apellido
ORDER BY puesto;


-- Consulta 15: Relaciones N:M con STRING_AGG y COALESCE
-- Detalle de cada servicio: qué se limpió (toda la vivienda, un área o un elemento),
-- quiénes lo atendieron y cuánto se cobró.
SELECT s.id_servicio, s.fecha, s.estado,
       STRING_AGG(DISTINCT ts.nombre || ' (' ||
                  COALESCE(te.nombre, ta.nombre, 'toda la vivienda') || ')', '; ') AS que_se_hizo,
       (SELECT STRING_AGG(e.nombre || ' ' || e.apellido, ', ')
        FROM asignacion a JOIN empleado e ON e.id_empleado = a.id_empleado
        WHERE a.id_servicio = s.id_servicio) AS empleados,
       SUM(d.precio_aplicado) AS total
FROM servicio s
JOIN detalle_servicio d ON d.id_servicio = s.id_servicio
JOIN tipo_servicio ts   ON ts.id_tipo_servicio = d.id_tipo_servicio
LEFT JOIN area a2          ON a2.id_area = d.id_area
LEFT JOIN tipo_area ta     ON ta.id_tipo_area = a2.id_tipo_area
LEFT JOIN elemento el      ON el.id_elemento = d.id_elemento
LEFT JOIN tipo_elemento te ON te.id_tipo_elemento = el.id_tipo_elemento
GROUP BY s.id_servicio, s.fecha, s.estado
ORDER BY s.fecha DESC;
